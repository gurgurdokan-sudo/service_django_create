```mermaid
flowchart TD
    %% レイヤー定義
    subgraph Sources [1. 基幹ソース (SQL抽出層)]
        S_Item[品目/在庫/受払<br/>MCFRAME/NEPSUS]
        S_Tori[取引先/設置先<br/>TASMAS/SMILE]
        S_Kiki[機器台帳/構成<br/>DWH/M-VIEW]
    end

    subgraph MDM_Logic [2. Django MDM (統合・クレンジング)]
        direction TB
        M_Identify{一意化ロジック}
        M_Link[紐付けロジック]
        
        subgraph Models [Django Models]
            Item[<b>品目マスタ</b><br/>SEISANスペック<br/>ロット管理フラグ]
            Partner[<b>取引先マスタ</b><br/>本社:請求先<br/>拠点:設置先]
            Equip[<b>機器マスタ</b><br/>シリアルNO<br/>親子階層構造]
        end
    end

    subgraph Destinations [3. 業務・外部出力層]
        direction TB
        H_Panel{{<b>現場制御盤</b><br/>SEISAN設定値送信}}
        F_SMILE[[<b>SMILE V</b><br/>インボイス/請求処理]]
        O_Servair[/<b>Servair</b><br/>現場リペア/点検/]
    end

    %% フロー接続
    %% 品目の流れ
    S_Item --> M_Identify
    M_Identify --> Item
    Item -->|工順・スペック| H_Panel
    Item -->|ロット管理| O_Servair

    %% 取引先の流れ (ENEOSの例)
    S_Tori --> M_Link
    M_Link -->|親:請求先| Partner
    M_Link -->|子:設置先| Partner
    Partner -->|インボイス/回収条件| F_SMILE

    %% 機器の流れ
    S_Kiki --> Equip
    Partner -->|ENEOS○○店に設置| Equip
    Item -->|この品目の機器| Equip

    %% ロット/シリアルの紐付け (トレーサビリティ)
    Equip -->|シリアル特定| O_Servair
    O_Servair -->|ロット不良時| Partner
    note1[ロット管理により<br/>特定部品の不具合から<br/>影響を受ける設置先を特定] -.-> O_Servair

    %% スタイル
    style Sources fill:#f5f5f5,stroke:#333
    style MDM_Logic fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style H_Panel fill:#bbdefb,stroke:#1976d2,stroke-width:2px
    style F_SMILE fill:#fff3e0,stroke:#ef6c00
    style O_Servair fill:#f3e5f5,stroke:#7b1fa2
```