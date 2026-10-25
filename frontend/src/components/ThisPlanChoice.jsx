import {useEffect, useRef, useState} from 'react';

const calcHours = (start, end) => {
    if (!start || !end) return 0;
    const [sh, sm] = start.split(':').map(Number);
    const [eh, em] = end.split(':').map(Number);
    const diffMinutes = (eh * 60 + em) - (sh * 60 + sm);
    return diffMinutes > 0 ? diffMinutes / 60 : 0;
}
const getCategory = (hours) => {
      if (hours <= 0) return "";
      if (hours < 3) return "<3";
      if (hours < 4) return "3-4";
      if (hours < 5) return "4-5";
      if (hours < 6) return "5-6";
      if (hours < 7) return "6-7";
      if (hours < 8) return "7-8";
      if (hours < 9) return "8-9";
      if (hours <= 10) return "9-10";
      return "";
}
const timeFetch = async (careLevel, strat, end, signal) => {
    const params = new URLSearchParams({ care_level:careLevel, start_time:strat, end_time:end })
    const response = await fetch(
        `/api/user/service_master_preview?${ params }`,
        { signal }
    );
    if (!response.ok) throw new Error("マスタを取得できませんでした");
    return await response.json();// APIは { category: "...", service_name:"..." } を返す
}
export default function ThisPlanChoice({careLevel}) {
    const [times, setTimes] = useState({start: "", end: ""});
    const [serviceName, setServiceName] = useState("");
    const [message, setMessage] = useState("時刻を入力してください");
    const cache = useRef(new Map());

    useEffect(() => {
        console.log("[入力欄Effect] start");
        const startTimeInput = document.getElementById('id_start_time');
        const endTimeInput = document.getElementById('id_end_time');
        if (!startTimeInput || !endTimeInput) {
          console.error("[入力欄Effect]入力欄が見つかりません");
          return;
        }
        const syncTimes = () => {
            const nextTimes ={start: startTimeInput.value, end: endTimeInput.value};
            console.log("[入力欄] 値:", nextTimes);
            setTimes(nextTimes);
        };
        syncTimes(); // 初期値のmatch
        startTimeInput.addEventListener("input", syncTimes);
        endTimeInput.addEventListener("input", syncTimes);
        return () => {
          console.log("[入力欄Effect] cleanup: リスナー解除");
          startTimeInput.removeEventListener("input", syncTimes);
          endTimeInput.removeEventListener("input", syncTimes);
        };
    }, []);
    const category = getCategory(calcHours(times.start, times.end));

    useEffect(() => {
        if (!category) {
            setServiceName("");
            setMessage("時間を入力してください");
            return;
        }

        const key = `${careLevel}:${category}`;
        console.log("[cache] key:", key, "hit:", cache.current.has(key));

        if (cache.current.has(key)) {
            const cachedName = cache.current.get(key);
            setServiceName(cachedName);
            setMessage(cachedName ? "" : "該当マスタなし");
            return;
        }

        const controller = new AbortController();
        setServiceName("");
        setMessage("取得中...");

        timeFetch(careLevel, times.start, times.end, controller.signal)
            .then((data) => {
                const name = data.service_name ?? "";
                cache.current.set(key, name); // 文字列だけ保存
                setServiceName(name);
                setMessage(name ? "" : "該当マスタなし");
            })
            .catch((error) => {
                if (error.name !== "AbortError") {
                    console.error("[API] 取得失敗:", error);
                    setMessage("取得に失敗しました");
                }
            });

        return () => controller.abort();
    }, [careLevel, times.start, times.end, category]);
    return <span className="text-primary fw-bold">{ serviceName || message }</span>
}