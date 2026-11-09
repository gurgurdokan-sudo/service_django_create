document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('userForm');
    if (!form) return;

    let isDirty = false;
    form.addEventListener('input', () => {
        isDirty = true;
    });
    form.addEventListener('change', () => {
        isDirty = true;
    });

    window.addEventListener('beforeunload', (e) => {
        if (!isDirty) return;
        e.preventDefault();
        e.returnValue = '';
    });

    const postalInput = document.getElementById('id_postal_code');
    const addressInput = document.getElementById('id_address');
    const lookupPostalCodeButton = document.getElementById('lookupPostalCode');
    const postalCodeMessage = document.getElementById('postalCodeMessage');
    const postalCandidatesWrap = document.getElementById('postalCandidatesWrap');
    const postalCandidates = document.getElementById('postalCandidates');
    let postalResults = [];

    const normalizePostalCode = (value) => value
        .replace(/[０-９]/g, (char) => String.fromCharCode(char.charCodeAt(0) - 0xFEE0))
        .replace(/[^0-9]/g, '');

    const setAddress = (result) => {
        if (!addressInput || !result) return;
        addressInput.value = `${result.address1 || ''}${result.address2 || ''}${result.address3 || ''}`;
        addressInput.dispatchEvent(new Event('input', {bubbles: true}));
        addressInput.dispatchEvent(new Event('change', {bubbles: true}));
    };

    const lookupPostalCode = async () => {
        if (!postalInput || !addressInput || !postalCodeMessage) return;
        const zipcode = normalizePostalCode(postalInput.value);
        postalCandidatesWrap.hidden = true;
        postalCandidates.replaceChildren(new Option('住所を選択してください', ''));
        postalResults = [];

        if (zipcode.length !== 7) {
            postalCodeMessage.textContent = '郵便番号を7桁で入力してください。';
            return;
        }

        postalCodeMessage.textContent = '住所を検索しています…';
        try {
            const url = new URL('https://zipcloud.ibsnet.co.jp/api/search');
            url.searchParams.set('zipcode', zipcode);
            const response = await fetch(url.toString());
            if (!response.ok) throw new Error('郵便番号APIへの接続に失敗しました。');

            const data = await response.json();
            if (data.status !== 200 || !Array.isArray(data.results) || data.results.length === 0) {
                postalCodeMessage.textContent = data.message || '住所が見つかりませんでした。';
                return;
            }

            postalResults = data.results;
            if (postalResults.length === 1) {
                setAddress(postalResults[0]);
                postalCodeMessage.textContent = '住所を入力しました。';
                return;
            }

            postalResults.forEach((result, index) => {
                const option = document.createElement('option');
                option.value = String(index);
                option.textContent = `${result.address1 || ''}${result.address2 || ''}${result.address3 || ''}`;
                postalCandidates.append(option);
            });
            postalCandidatesWrap.hidden = false;
            postalCodeMessage.textContent = '住所候補を選択してください。';
        } catch (error) {
            console.error(error);
            postalCodeMessage.textContent = '住所を検索できませんでした。時間をおいて再度お試しください。';
        }
    };

    if (lookupPostalCodeButton) {
        lookupPostalCodeButton.addEventListener('click', lookupPostalCode);
    }
    if (postalInput) {
        postalInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                lookupPostalCode();
            }
        });
        postalInput.addEventListener('input', () => {
            if (postalCodeMessage) postalCodeMessage.textContent = '';
            if (postalCandidatesWrap) postalCandidatesWrap.hidden = true;
        });
    }
    if (postalCandidates) {
        postalCandidates.addEventListener('change', () => {
            const result = postalResults[Number(postalCandidates.value)];
            if (result) {
                setAddress(result);
                postalCodeMessage.textContent = '住所を入力しました。';
            }
        });
    }

    const birthDateInput = document.getElementById('id_date_of_birth');
    const currentAge = document.getElementById('currentAge');
    const openWarekiConverter = document.getElementById('openWarekiConverter');
    const warekiConverter = document.getElementById('warekiConverter');
    const warekiEraSelect = document.getElementById('warekiEraSelect');
    const warekiYear = document.getElementById('warekiYear');
    const warekiMonth = document.getElementById('warekiMonth');
    const warekiDay = document.getElementById('warekiDay');
    const warekiPreview = document.getElementById('warekiPreview');
    const applyWarekiDate = document.getElementById('applyWarekiDate');
    const closeWarekiConverter = document.getElementById('closeWarekiConverter');

    const parseDateInput = (value) => {
        const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || '');
        if (!match) return null;
        const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
        if (date.getFullYear() !== Number(match[1]) ||
            date.getMonth() !== Number(match[2]) - 1 ||
            date.getDate() !== Number(match[3])) return null;
        return date;
    };

    const updateAge = () => {
        if (!birthDateInput || !currentAge) return;
        const birthDate = parseDateInput(birthDateInput.value);
        if (!birthDate) {
            currentAge.textContent = '';
            return;
        }
        const today = new Date();
        let age = today.getFullYear() - birthDate.getFullYear();
        if (today.getMonth() < birthDate.getMonth() ||
            (today.getMonth() === birthDate.getMonth() && today.getDate() < birthDate.getDate())) {
            age -= 1;
        }
        currentAge.textContent = age < 0 ? '生年月日を確認してください。' : `現在 ${age} 歳`;
    };

    const warekiFormatter = new Intl.DateTimeFormat('ja-JP-u-ca-japanese', {
        era: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    const eraDefinitions = {
        '令和': {start: '2019-05-01', end: null},
        '平成': {start: '1989-01-08', end: '2019-04-30'},
        '昭和': {start: '1926-12-25', end: '1989-01-07'},
        '大正': {start: '1912-07-30', end: '1926-12-24'},
        '明治': {start: '1868-10-23', end: '1912-07-29'}
    };

    const getWareki = (date) => {
        const era = warekiFormatter.formatToParts(date).find((part) => part.type === 'era')?.value;
        return {era, text: warekiFormatter.format(date)};
    };

    const toIsoDate = (date) => [
        String(date.getFullYear()).padStart(4, '0'),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0')
    ].join('-');

    const getDateFromWareki = () => {
        if (!warekiEraSelect || !warekiYear || !warekiMonth || !warekiDay) {
            return {error: '年号・年・月・日を入力してください。'};
        }
        const era = warekiEraSelect.value;
        const year = Number(warekiYear.value);
        const month = Number(warekiMonth.value);
        const day = Number(warekiDay.value);
        const definition = eraDefinitions[era];
        if (!definition || !Number.isInteger(year) || year < 1 ||
            !Number.isInteger(month) || month < 1 || month > 12 ||
            !Number.isInteger(day) || day < 1 || day > 31) {
            return {error: '年号・年・月・日を正しく入力してください。'};
        }

        const date = new Date(Number(definition.start.slice(0, 4)) + year - 1, month - 1, day);
        if (date.getFullYear() !== Number(definition.start.slice(0, 4)) + year - 1 ||
            date.getMonth() !== month - 1 || date.getDate() !== day) {
            return {error: '存在する日付を入力してください。'};
        }
        const eraStart = parseDateInput(definition.start);
        const eraEnd = definition.end ? parseDateInput(definition.end) : null;
        if (date < eraStart || (eraEnd && date > eraEnd)) {
            return {error: '入力した日付は選択した年号の期間外です。'};
        }
        return {date, era, year, month, day};
    };

    const updateWarekiPreview = () => {
        if (!warekiPreview || !applyWarekiDate) return;
        const converted = getDateFromWareki();
        if (converted.error) {
            warekiPreview.textContent = converted.error;
            applyWarekiDate.disabled = true;
            return;
        }
        const yearLabel = converted.year === 1 ? '元' : String(converted.year);
        warekiPreview.textContent = `変換結果：${converted.era}${yearLabel}年${converted.month}月${converted.day}日（西暦 ${toIsoDate(converted.date)}）`;
        applyWarekiDate.disabled = false;
    };

    if (birthDateInput) {
        birthDateInput.addEventListener('input', updateAge);
        birthDateInput.addEventListener('change', updateAge);
        updateAge();
    }
    if (openWarekiConverter && warekiConverter) {
        openWarekiConverter.addEventListener('click', () => {
            const currentDate = birthDateInput ? parseDateInput(birthDateInput.value) : null;
            const currentEra = currentDate ? getWareki(currentDate).era : '';
            const definition = eraDefinitions[currentEra];
            if (warekiEraSelect) warekiEraSelect.value = definition ? currentEra : '';
            if (warekiYear) warekiYear.value = currentDate && definition
                ? String(currentDate.getFullYear() - Number(definition.start.slice(0, 4)) + 1) : '';
            if (warekiMonth) warekiMonth.value = currentDate ? String(currentDate.getMonth() + 1) : '';
            if (warekiDay) warekiDay.value = currentDate ? String(currentDate.getDate()) : '';
            warekiConverter.hidden = false;
            updateWarekiPreview();
        });
    }
    [warekiEraSelect, warekiYear, warekiMonth, warekiDay].forEach((input) => {
        if (input) input.addEventListener('input', updateWarekiPreview);
        if (input && input.tagName === 'SELECT') input.addEventListener('change', updateWarekiPreview);
    });
    if (applyWarekiDate) {
        applyWarekiDate.addEventListener('click', () => {
            if (!birthDateInput) return;
            const converted = getDateFromWareki();
            if (converted.error) {
                updateWarekiPreview();
                return;
            }
            birthDateInput.value = toIsoDate(converted.date);
            birthDateInput.dispatchEvent(new Event('input', {bubbles: true}));
            birthDateInput.dispatchEvent(new Event('change', {bubbles: true}));
            warekiConverter.hidden = true;
        });
    }
    if (closeWarekiConverter && warekiConverter) {
        closeWarekiConverter.addEventListener('click', () => {
            warekiConverter.hidden = true;
        });
    }

    form.addEventListener('submit', () => {
        const btn = form.querySelector('button[value="save"]');
        if (btn) setTimeout(() => {
            btn.disabled = true;
        }, 1);
        isDirty = false;
    });
});