from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from dashboard.context_processors import get_office
from dashboard.forms import OfficeSettingForm
from dashboard.models import AddOnService, OfficeAddOnSetting, Office
from employees.permissions import delete_permission_required, has_delete_permission

import logging
logger = logging.getLogger(__name__)

@delete_permission_required
def office_setting(request):
    office: Office = get_office(request)
    if office is None:
        logger.warning(
            "事務所に紐づかないユーザー: user_id=%s",
            getattr(request.user, "pk", None),
        )
        return redirect("dashboard:user_list")

    if request.method == "POST":
        # 加算設定のアーカイブはPATCH APIでis_archived=Trueに更新
        action = request.POST.get("action")

        if action == "save_addon_settings":
            enabled_ids = set(request.POST.getlist("enabled_addon_ids"))
            with transaction.atomic():
                # 通常画面に表示している設定だけを更新し、アーカイブ済み行は変更しない
                settings: list[OfficeAddOnSetting] = list(
                    OfficeAddOnSetting.objects.filter(
                        office=office,
                        is_archived=False,
                    )
                )
                changed = []
                for setting in settings:
                    enabled = str(setting.addon_id) in enabled_ids
                    if setting.is_enabled != enabled:
                        setting.is_enabled = enabled
                        changed.append(setting)
                if changed:
                    OfficeAddOnSetting.objects.bulk_update(
                        changed, ["is_enabled"]
                    )
            messages.success(request, "加算の表示設定を保存しました。")
            return redirect(request.path)

        if action == "add_addon_setting":
            addon = get_object_or_404(
                AddOnService,
                pk=request.POST.get("addon_id"),
            )
            OfficeAddOnSetting.objects.get_or_create(
                office=office,
                addon=addon,
                defaults={"is_enabled": True, "is_archived": False},
            )
            messages.success(request, "加算をこの事業所に追加しました。")
            return redirect(request.path)

        form = OfficeSettingForm(request.POST, instance=office)
        if form.is_valid():
            form.save()
            messages.success(request, "事務所情報を保存しました。")
            return redirect(request.path)
    else:
        form = OfficeSettingForm(instance=office)

    # is_archived=Trueの設定は出さない
    addon_settings = (
        OfficeAddOnSetting.objects
        .filter(office=office, is_archived=False)
        .select_related("addon")
        .order_by("addon__service_name")
    )
    available_addons = (
        AddOnService.objects
        .exclude(office_settings__office=office)
        .order_by("service_name")
    )

    display_labels = {}
    for field in office._meta.fields:
        if field.primary_key:
            continue
        value = getattr(office, field.name)
        display_labels[field.verbose_name] = value if value is not None else "-"

    return render(request, "dashboard/office_setting.html", {
        "display_labels": display_labels,
        "form": form,
        "addon_settings": addon_settings,
        "available_addons": available_addons,
    })

@api_view(["PATCH"])
def update_office_addon_setting(request):
    if not has_delete_permission(request.user):
        return Response(
            {"status": "error", "message": "設定変更の権限がありません。"},
            status=status.HTTP_403_FORBIDDEN,
        )

    office = get_office(request)
    if office is None:
        return Response(
            {"status": "error", "message": "事業所が設定されていません。"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    addon_id = request.data.get("addon_id")
    fields = [field for field in ("is_enabled", "is_archived") if field in request.data]
    if addon_id is None or len(fields) != 1:
        return Response(
            {"status": "error", "message": "加算IDまたは更新項目が不正です。"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    field = fields[0]
    value = request.data.get(field)
    if not isinstance(value, bool):
        return Response(
            {"status": "error", "message": "設定値はtrueまたはfalseで指定してください。"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # アーカイブ（True）はAPIで設定
    if field == "is_archived" and value is False:
        return Response(
            {"status": "error", "message": "アーカイブ設定の復元は、お問い合わせください。"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    setting = get_object_or_404(
        OfficeAddOnSetting,
        office=office,
        addon_id=addon_id,
    )
    if getattr(setting, field) != value:
        setattr(setting, field, value)
        setting.save(update_fields=[field])

    return Response({
        "status": "ok",
        "addon_id": setting.addon_id,
        field: getattr(setting, field),
    })