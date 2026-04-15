flowchart TD
    %% 1. 基幹ソース (SQL抽出層)
    subgraph Sources ["1. 基幹ソース (SQL抽出層)"]
        S_Item["品目/在庫/受払<br/>MCFRAME/NEPSUS"]
        S_Tori["取引先/設置先<br/>TASMAS/SMILE"]
        S_Kiki["機器台帳/構成<br/>DWH/M-VIEW"]
    end

    subgraph MDM_Logic ["2. Django MDM (統合・クレンジング)"]
        direction TB
        M_Identify{"一意化ロジック"}
        M_Link["紐付けロジック"]
        
        subgraph Models ["Django Models"]
            Item["品目マスタ<br/>SEISANスペック<br/>ロット管理フラグ"]
            Partner["取引先マスタ<br/>本社:請求先<br/>拠点:設置先"]
            Equip["機器マスタ<br/>シリアルNO<br/>親子階層構造"]
        end
    end

    subgraph Destinations ["3. 業務・外部出力層"]
        direction TB
        H_Panel{{"現場制御盤<br/>SEISAN設定値送信"}}
        F_SMILE[["SMILE V<br/>インボイス/請求処理"]]
        O_Servair[/"Servair<br/>現場リペア/点検/" ]
    end

    %% フロー接続
    S_Item --> M_Identify
    M_Identify --> Item
    Item -->|"工順・スペック"| H_Panel
    Item -->|"ロット管理"| O_Servair

    S_Tori --> M_Link
    M_Link -->|"親:請求先"| Partner
    M_Link -->|"子:設置先"| Partner
    Partner -->|"インボイス/回収条件"| F_SMILE

    S_Kiki --> Equip
    Partner -->|"ENEOS○○店に設置"| Equip
    Item -->|"この品目の機器"| Equip

    Equip -->|"シリアル特定"| O_Servair
    O_Servair -->|"ロット不具合調査"| Partner

    %% スタイル設定
    style Sources fill:#f5f5f5,stroke:#333
    style MDM_Logic fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style H_Panel fill:#bbdefb,stroke:#1976d2,stroke-width:2px
    style F_SMILE fill:#fff3e0,stroke:#ef6c00
    style O_Servair fill:#f3e5f5,stroke:#7b1fa2