'''カレンダーのポップアップ操作用JSON API'''
from datetime import date as date_cls, time as time_cls

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Assignment, Employee, ShiftPattern


def _parse_time(value):
    if not value:
        return None
    try:
        hour, minute = str(value).split(':')[:2]
        return time_cls(int(hour), int(minute))
    except (ValueError, TypeError):
        return None


@api_view(['POST'])
def assignment_save(request):
    '''担当スケジュールの作成/更新（idがあれば更新）

    register_pattern=true なら同じ曜日・時間でシフトパターンにも登録する。
    '''
    data = request.data
    try:
        target_date = date_cls.fromisoformat(str(data.get('date')))
        employee = Employee.objects.get(id=data.get('employee'))
    except (ValueError, TypeError, Employee.DoesNotExist):
        return Response({'status': 'error', 'message': '日付または従業員が不正です'}, status=400)

    from dashboard.models import User
    try:
        care_user = User.objects.get(id=data.get('user'))
    except (User.DoesNotExist, ValueError, TypeError):
        return Response({'status': 'error', 'message': '利用者が不正です'}, status=400)

    fields = {
        'employee': employee,
        'user': care_user,
        'date': target_date,
        'start_time': _parse_time(data.get('start_time')),
        'end_time': _parse_time(data.get('end_time')),
        'is_daily_reporter': bool(data.get('is_daily_reporter')),
        'note': (data.get('note') or '')[:200],
    }

    assignment_id = data.get('id')
    duplicate = Assignment.objects.filter(
        employee=employee, user=care_user, date=target_date,
    ).exclude(id=assignment_id or None)
    if duplicate.exists():
        return Response({'status': 'error',
                         'message': '同じ日付・従業員・利用者の割当てが既にあります'}, status=400)

    if assignment_id:
        updated = Assignment.objects.filter(id=assignment_id).update(**{
            key: value for key, value in fields.items()
        })
        if not updated:
            return Response({'status': 'error', 'message': '対象が見つかりません'}, status=404)
        assignment = Assignment.objects.get(id=assignment_id)
    else:
        assignment = Assignment.objects.create(**fields)

    pattern_registered = False
    if data.get('register_pattern'):
        _, pattern_registered = ShiftPattern.objects.get_or_create(
            employee=employee, user=care_user, weekday=target_date.weekday(),
            defaults={
                'start_time': fields['start_time'],
                'end_time': fields['end_time'],
                'is_daily_reporter': fields['is_daily_reporter'],
            },
        )

    return Response({'status': 'ok', 'id': assignment.id,
                     'pattern_registered': pattern_registered})


@api_view(['POST'])
def assignment_delete(request, assignment_id):
    deleted, _ = Assignment.objects.filter(id=assignment_id).delete()
    if not deleted:
        return Response({'status': 'error', 'message': '対象が見つかりません'}, status=404)
    return Response({'status': 'ok'})


@api_view(['POST'])
def pattern_toggle(request, pattern_id):
    '''シフトパターンの有効/無効を切り替える'''
    try:
        pattern = ShiftPattern.objects.get(id=pattern_id)
    except ShiftPattern.DoesNotExist:
        return Response({'status': 'error', 'message': '対象が見つかりません'}, status=404)
    pattern.is_active = not pattern.is_active
    pattern.save(update_fields=['is_active'])
    return Response({'status': 'ok', 'is_active': pattern.is_active})
