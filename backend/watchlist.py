# Watchlist — hierarchy: 地區 > 産業 > 細分類 (> 四級分類)
# Leaf values are lists of {symbol, name, name_en, tags}
# Branch values are dicts of sub-categories
# tags: short descriptor labels shown as chips in the sidebar

WATCHLIST = {
    "台灣": {
        "半導體": {
            "晶圓代工": [
                {"symbol": "2330.TW",  "name": "台積電",       "name_en": "TSMC",                              "tags": ["邏輯代工", "先進製程 N3/N2"]},
                {"symbol": "2303.TW",  "name": "聯電",         "name_en": "UMC",                               "tags": ["成熟製程", "特殊製程 28nm+"]},
                {"symbol": "5347.TWO", "name": "世界先進",     "name_en": "Vanguard International Semiconductor","tags": ["PMIC/Driver代工", "8吋廠"]},
                {"symbol": "6770.TW",  "name": "力積電",       "name_en": "Powerchip Semiconductor (PSMC)",    "tags": ["DRAM/Logic代工", "12吋"]},
                {"symbol": "6789.TW",  "name": "采鈺科技",     "name_en": "VisEra Technologies",               "tags": ["CIS背照式代工", "CMOS影像感測"]},
                {"symbol": "8028.TW",  "name": "昇陽半導體",   "name_en": "Eris Technology Corp",              "tags": ["6吋代工", "分立元件"]},
            ],
            "IC設計": [
                {"symbol": "2454.TW",  "name": "聯發科技",     "name_en": "MediaTek",                          "tags": ["AP/5G SoC", "AIoT"]},
                {"symbol": "3034.TW",  "name": "聯詠科技",     "name_en": "Novatek Microelectronics",          "tags": ["顯示驅動IC", "TDDI"]},
                {"symbol": "2379.TW",  "name": "瑞昱半導體",   "name_en": "Realtek Semiconductor",             "tags": ["網路晶片", "WiFi/藍牙"]},
                {"symbol": "3443.TW",  "name": "創意電子",     "name_en": "Global Unichip (GUC)",              "tags": ["ASIC設計服務", "CoWoS IP"]},
                {"symbol": "3035.TW",  "name": "智原科技",     "name_en": "Faraday Technology",                "tags": ["ASIC IP授權", "SoC設計服務"]},
                {"symbol": "5274.TWO", "name": "信驊科技",     "name_en": "Aspeed Technology",                 "tags": ["BMC伺服器管理IC", "AI伺服器"]},
                {"symbol": "3529.TWO", "name": "力旺電子",     "name_en": "eMemory Technology",                "tags": ["嵌入式NVM IP", "eFlash/eMCM"]},
                {"symbol": "3661.TW",  "name": "世芯-KY",      "name_en": "Alchip Technologies",               "tags": ["HPC/AI ASIC", "7nm以下先進製程"]},
                {"symbol": "8016.TW",  "name": "矽創電子",     "name_en": "Sitronix Technology",               "tags": ["顯示驅動IC", "觸控IC"]},
                {"symbol": "4966.TWO", "name": "譜瑞-KY",      "name_en": "Parade Technologies",               "tags": ["顯示介面IC", "TCON/eDP"]},
                {"symbol": "6756.TW",  "name": "威鋒電子",     "name_en": "VIA Labs",                          "tags": ["USB Hub/Switch", "PCIe介面"]},
                {"symbol": "6415.TW",  "name": "矽力-KY",      "name_en": "Silergy Corp",                      "tags": ["PMIC", "電源管理IC"]},
                {"symbol": "6202.TW",  "name": "盛群半導體",   "name_en": "Holtek Semiconductor",              "tags": ["MCU", "USB/藍牙控制"]},
                {"symbol": "6643.TWO", "name": "M31科技",      "name_en": "M31 Technology Corp",               "tags": ["矽智財 PHY IP", "SerDes"]},
                {"symbol": "3227.TWO", "name": "原相科技",     "name_en": "PixArt Imaging",                    "tags": ["光學感測器", "影像處理IC"]},
                {"symbol": "2458.TW",  "name": "義隆電子",     "name_en": "ELAN Microelectronics",             "tags": ["觸控IC", "指紋辨識IC"]},
                {"symbol": "6531.TW",  "name": "愛普科技",     "name_en": "Apex Technologies",                 "tags": ["TCON時序控制", "顯示IC"]},
            ],
            "記憶體": [
                {"symbol": "2408.TW",  "name": "南亞科技",     "name_en": "Nanya Technology",                  "tags": ["DRAM", "Specialty DRAM"]},
                {"symbol": "2337.TW",  "name": "旺宏電子",     "name_en": "Macronix International",            "tags": ["NOR Flash", "SLC NAND"]},
                {"symbol": "2344.TW",  "name": "華邦電子",     "name_en": "Winbond Electronics",               "tags": ["NOR Flash", "低功耗DRAM"]},
                {"symbol": "8299.TWO", "name": "群聯電子",     "name_en": "Phison Electronics",                "tags": ["NAND主控", "SSD/eMMC方案"]},
                {"symbol": "6286.TW",  "name": "慧榮科技",     "name_en": "Silicon Motion",                    "tags": ["NAND主控", "eMMC/UFS"]},
                {"symbol": "4919.TW",  "name": "新唐科技",     "name_en": "Nuvoton Technology",                "tags": ["MCU", "NOR Flash"]},
                {"symbol": "3260.TWO", "name": "威剛科技",     "name_en": "ADATA Technology",                  "tags": ["DRAM模組", "SSD品牌通路"]},
                {"symbol": "2451.TW",  "name": "創見資訊",     "name_en": "Transcend Information",             "tags": ["工業記憶體模組", "工業SSD"]},
                {"symbol": "4967.TW",  "name": "十銓科技",     "name_en": "Team Group",                        "tags": ["電競DRAM模組", "SSD"]},
            ],
            "封裝測試": {
                "封測廠": [
                    {"symbol": "2311.TW",  "name": "日月光投控", "name_en": "ASE Technology Holding",          "tags": ["全球最大封測", "先進封裝 SiP/Fan-out"]},
                    {"symbol": "6239.TW",  "name": "力成科技",   "name_en": "Powertech Technology",            "tags": ["DRAM封測", "HBM測試"]},
                    {"symbol": "2449.TW",  "name": "京元電子",   "name_en": "King Yuan Electronics",           "tags": ["IC測試", "晶圓級測試"]},
                    {"symbol": "3264.TWO", "name": "欣銓科技",   "name_en": "Chipbond Technology",             "tags": ["驅動IC封測", "CoF/COG"]},
                    {"symbol": "6257.TW",  "name": "矽格半導體", "name_en": "Sigurd Microelectronics",         "tags": ["類比/功率IC封測"]},
                    {"symbol": "2329.TW",  "name": "華泰電子",   "name_en": "HMC Hwa Mei Corporation",         "tags": ["導線架封裝", "MCU/功率"]},
                    {"symbol": "8110.TW",  "name": "華東科技",   "name_en": "Hua Tong Electronic",             "tags": ["LCD驅動IC封裝"]},
                ],
                "探針卡": [
                    {"symbol": "6510.TWO", "name": "精測電子",   "name_en": "Chunghwa Precision Test Tech",    "tags": ["高速探針卡", "HBM/AI晶片測試"]},
                    {"symbol": "6223.TWO", "name": "旺矽科技",   "name_en": "MJC Probe",                       "tags": ["DRAM探針卡", "垂直型探針"]},
                ],
                "IC載板": [
                    {"symbol": "3189.TW",  "name": "景碩科技",   "name_en": "Kinsus Interconnect Technology",  "tags": ["ABF載板", "FC-BGA"]},
                    {"symbol": "3037.TW",  "name": "欣興電子",   "name_en": "Unimicron Technology",            "tags": ["ABF/BT載板", "HDI軟板"]},
                    {"symbol": "8046.TW",  "name": "南電",        "name_en": "Nan Ya PCB",                      "tags": ["ABF載板", "伺服器GPU封裝"]},
                    {"symbol": "4958.TW",  "name": "臻鼎科技",   "name_en": "Zhen Ding Technology",            "tags": ["HDI軟硬板", "FPC", "蘋果供應鏈"]},
                ],
            },
            "功率元件": [
                {"symbol": "3707.TWO", "name": "漢磊科技",     "name_en": "Han Lei Technology",                "tags": ["SiC磊晶代工", "GaN Epi"]},
                {"symbol": "8255.TWO", "name": "朋程科技",     "name_en": "Anpec Electronics",                 "tags": ["整流橋", "車用電源IC"]},
                {"symbol": "2481.TW",  "name": "強茂",         "name_en": "General Semiconductor",             "tags": ["TVS/Zener", "整流器"]},
                {"symbol": "5425.TWO", "name": "台半",         "name_en": "Taiwan Semiconductor Co.",          "tags": ["功率MOSFET", "整流器"]},
                {"symbol": "3105.TWO", "name": "穩懋半導體",   "name_en": "WIN Semiconductors",                "tags": ["GaN PA", "5G RF前端"]},
                {"symbol": "8086.TWO", "name": "宏捷科技",     "name_en": "Advanced Wireless Semiconductor",   "tags": ["GaAs PA", "5G毫米波RF"]},
                {"symbol": "5299.TWO", "name": "杰力科技",     "name_en": "Jetek Semiconductor",               "tags": ["功率MOSFET", "GaN充電"]},
                {"symbol": "3675.TWO", "name": "德微科技",     "name_en": "De Wei Technology",                 "tags": ["功率離散元件", "MOSFET/整流"]},
                {"symbol": "2342.TW",  "name": "茂矽電子",     "name_en": "MoselVitelic",                      "tags": ["MOSFET", "功率IC"]},
                {"symbol": "3317.TWO", "name": "尼克森微",     "name_en": "Niko Semiconductor",                "tags": ["功率MOSFET", "小封裝"]},
                {"symbol": "2455.TW",  "name": "全新光電",     "name_en": "Advanced Photonics",                "tags": ["LED晶粒", "化合物半導體"]},
                {"symbol": "6616.TWO", "name": "特昇科技",     "name_en": "Teresic Technology",                "tags": ["SiC基板/磊晶"]},
                {"symbol": "6104.TWO", "name": "創杰科技",     "name_en": "Carsem Semiconductor",              "tags": ["GaN RF PA"]},
                {"symbol": "2448.TW",  "name": "晶元光電",     "name_en": "Epistar",                           "tags": ["LED晶粒", "Mini/Micro LED"]},
            ],
            "材料": [
                # 晶圓 / 基板
                {"symbol": "6488.TWO", "name": "環球晶圓",     "name_en": "GlobalWafers",                      "tags": ["矽晶圓", "全球前三大"]},
                {"symbol": "6182.TWO", "name": "合晶科技",     "name_en": "Sino-American Silicon",             "tags": ["矽晶圓 CZ/FZ", "6\"/8\""]},
                {"symbol": "3532.TW",  "name": "台勝科",       "name_en": "Episil Technologies",               "tags": ["矽晶圓", "12吋拋光片"]},
                {"symbol": "3016.TW",  "name": "嘉晶電子",     "name_en": "Episil-Precision",                  "tags": ["SiC/GaN磊晶片", "6吋"]},
                # 化學品
                {"symbol": "1711.TW",  "name": "永光化學",     "name_en": "Ever Light Chemical",               "tags": ["光阻材料", "OLED有機材料"]},
                {"symbol": "1717.TW",  "name": "長興材料",     "name_en": "Chang Chun Group",                  "tags": ["CMP研磨液", "PCB濕製程"]},
                {"symbol": "4552.TW",  "name": "力拓科技",     "name_en": "Leatec Fine Ceramics",              "tags": ["石英/陶瓷零件", "製程耗材"]},
                {"symbol": "4503.TWO", "name": "金洲精密",     "name_en": "Chin Chou Precision",               "tags": ["石英製品", "精密零件"]},
                {"symbol": "1323.TW",  "name": "永裕",         "name_en": "Yung Yu Chemical",                  "tags": ["工業氣體容器", "鋼瓶"]},
                {"symbol": "1760.TW",  "name": "寶一化學",     "name_en": "Pac-Tech Chemical",                 "tags": ["蝕刻液", "製程化學品"]},
                {"symbol": "6646.TW",  "name": "日揚科技",     "name_en": "Scientech (process)",               "tags": ["爐管設備", "熱處理製程"]},
                # 精密材料 / 研磨 / 耗材
                {"symbol": "1560.TW",  "name": "中砂",         "name_en": "Kinik Company",                     "tags": ["CMP研磨墊", "鑽石線鋸"]},
                {"symbol": "4768.TWO", "name": "晶呈科技",     "name_en": "Cryscore Optoelectronic",           "tags": ["SiC研磨材料", "化學機械研磨"]},
                {"symbol": "4772.TWO", "name": "台特化",       "name_en": "Taiwan Speciality Chemicals",       "tags": ["特殊製程化學品", "前段濕製程"]},
                {"symbol": "5434.TW",  "name": "崇越科技",     "name_en": "Topco Scientific",                  "tags": ["半導體材料代理", "氣體通路商"]},
                {"symbol": "3680.TWO", "name": "家登精密",     "name_en": "Gudeng Precision Industrial",       "tags": ["光罩盒 FOUP/FOSB", "前開式晶圓盒"]},
            ],
            "設備": [
                {"symbol": "2404.TW",  "name": "漢唐集成",     "name_en": "Han Tang Systems",                  "tags": ["無塵室廠務機電", "EPC系統整合"]},
                {"symbol": "6196.TW",  "name": "帆宣系統",     "name_en": "Marketech International",           "tags": ["廠務管路/氣體系統", "EPC整合"]},
                {"symbol": "6139.TW",  "name": "亞翔工程",     "name_en": "Asia Allied Infrastructure",        "tags": ["無塵室建設", "廠務工程"]},
                {"symbol": "5536.TWO", "name": "聖暉企業",     "name_en": "Summit Grand Enterprise",           "tags": ["機電工程", "廠務維運"]},
                {"symbol": "6691.TW",  "name": "洋基工程",     "name_en": "Yankee Engineering Corp",           "tags": ["工業氣體管路", "高壓氣體系統"]},
                {"symbol": "3131.TWO", "name": "弘塑科技",     "name_en": "Hung Hing Precision Technology",    "tags": ["濕式清洗/蝕刻設備"]},
                {"symbol": "3583.TW",  "name": "辛耘企業",     "name_en": "Scientech Corp",                    "tags": ["濕式製程設備", "晶圓清洗"]},
                {"symbol": "3413.TW",  "name": "京鼎精密",     "name_en": "Kinergy Advanced Technology",       "tags": ["CVD/ALD設備零組件"]},
                {"symbol": "6187.TWO", "name": "萬潤科技",     "name_en": "Wan Jung Technology",               "tags": ["AOI光學檢測設備", "點膠設備"]},
                {"symbol": "3167.TW",  "name": "大量電子",     "name_en": "Daliwa Electronics",                "tags": ["半導體設備零組件"]},
            ],
            "半導體ETF": [
                {"symbol": "00891.TW", "name": "中信關鍵半導體","name_en": "CTBC Key Semiconductor ETF",        "tags": ["台灣半導體", "主動式ETF"]},
                {"symbol": "00892.TW", "name": "富邦台灣半導體","name_en": "Fubon Taiwan Semiconductor ETF",    "tags": ["市值加權", "台積電高比重"]},
                {"symbol": "00904.TW", "name": "新光台灣半導體","name_en": "Shin Kong TW Semiconductor ETF",   "tags": ["等權重30檔", "中小型分散"]},
                {"symbol": "00913.TW", "name": "半導體科技ETF", "name_en": "Semiconductor Tech ETF",           "tags": ["20檔半導體", "中小型"]},
                {"symbol": "00927.TW", "name": "群益半導體收益","name_en": "Capital Semiconductor Income ETF",  "tags": ["季配息", "高股息半導體"]},
                {"symbol": "00947.TW", "name": "元大AI半導體",  "name_en": "Yuanta Global AI Semiconductor ETF","tags": ["AI半導體", "全球布局"]},
            ],
        },

        "科技系統廠": {
            "EMS/AI服務器": [
                {"symbol": "2317.TW",  "name": "鴻海精密",     "name_en": "Hon Hai Precision (Foxconn)",       "tags": ["全球最大EMS", "AI伺服器/GB200"]},
                {"symbol": "2382.TW",  "name": "廣達電腦",     "name_en": "Quanta Computer",                   "tags": ["雲端AI伺服器", "Nvidia DGX代工"]},
                {"symbol": "3231.TW",  "name": "緯創資通",     "name_en": "Wistron Corporation",               "tags": ["AI機架伺服器", "CSP客戶"]},
                {"symbol": "6669.TW",  "name": "緯穎科技",     "name_en": "Wiwynn Corporation",                "tags": ["超大規模雲端伺服器", "CSP專供"]},
                {"symbol": "2356.TW",  "name": "英業達",       "name_en": "Inventec Corporation",              "tags": ["AI伺服器", "筆電/電信"]},
                {"symbol": "2324.TW",  "name": "仁寶電腦",     "name_en": "Compal Electronics",                "tags": ["筆電代工", "AI伺服器"]},
                {"symbol": "4938.TW",  "name": "和碩聯合科技", "name_en": "Pegatron Corporation",              "tags": ["iPhone/消費電子代工", "伺服器"]},
                {"symbol": "3706.TW",  "name": "神達電腦",     "name_en": "MiTAC Holdings",                    "tags": ["工業電腦/伺服器", "MiTAC品牌"]},
            ],
            "品牌PC/主板/電競": [
                {"symbol": "2357.TW",  "name": "華碩電腦",     "name_en": "ASUSTeK Computer",                  "tags": ["消費/商用電腦", "AI PC/主板/顯卡"]},
                {"symbol": "2353.TW",  "name": "宏碁",         "name_en": "Acer Inc.",                         "tags": ["全球筆電品牌", "Chromebook"]},
                {"symbol": "2376.TW",  "name": "技嘉科技",     "name_en": "Gigabyte Technology",               "tags": ["主板/顯卡", "AI伺服器機架"]},
                {"symbol": "2377.TW",  "name": "微星科技",     "name_en": "MSI (Micro-Star International)",    "tags": ["電競主板/顯卡", "電競筆電"]},
            ],
            "工業電腦/邊緣運算": [
                {"symbol": "2395.TW",  "name": "研華科技",     "name_en": "Advantech Co.",                     "tags": ["工業電腦全球龍頭", "IoT/AIoT平台"]},
                {"symbol": "2352.TW",  "name": "佳世達科技",   "name_en": "Qisda Corporation",                 "tags": ["商用顯示器", "醫療設備"]},
                {"symbol": "3706.TW",  "name": "神達電腦",     "name_en": "MiTAC Holdings",                    "tags": ["嵌入式電腦", "車載/工控"]},
            ],
            "電源/散熱/機電": [
                {"symbol": "2308.TW",  "name": "台達電子",     "name_en": "Delta Electronics",                 "tags": ["電源供應器", "散熱/儲能/EV充電"]},
                {"symbol": "2301.TW",  "name": "光寶科技",     "name_en": "Lite-On Technology",                "tags": ["電源供應器", "LED/相機模組"]},
                {"symbol": "8210.TW",  "name": "勤誠興業",     "name_en": "Chenbro Micom",                     "tags": ["伺服器機殼", "散熱模組"]},
                {"symbol": "3017.TW",  "name": "奇鋐科技",     "name_en": "Asia Vital Components (AVC)",       "tags": ["CPU/GPU散熱", "液冷模組"]},
                {"symbol": "3324.TWO", "name": "雙鴻科技",     "name_en": "Shuang Hong Technology",            "tags": ["均熱板/散熱板", "液冷板"]},
            ],
            "PCB": [
                {"symbol": "3189.TW",  "name": "景碩科技",     "name_en": "Kinsus Interconnect Technology",    "tags": ["ABF載板", "FC-BGA"]},
                {"symbol": "3037.TW",  "name": "欣興電子",     "name_en": "Unimicron Technology",              "tags": ["ABF/BT載板", "HDI軟板"]},
                {"symbol": "3363.TWO", "name": "上诠",         "name_en": "Compeq Manufacturing",              "tags": ["柔性電路板", "FPC/軟板"]},
                {"symbol": "8046.TW",  "name": "南電",          "name_en": "Nan Ya PCB",                        "tags": ["ABF載板", "伺服器GPU封裝"]},
                {"symbol": "1519.TW",  "name": "華城",         "name_en": "Hwa Chuang Electronics",            "tags": ["多層硬板", "通訊PCB"]},
                {"symbol": "3163.TWO", "name": "波若威",       "name_en": "Powertec Technology",              "tags": ["精密電路板", "IC載板"]},
                {"symbol": "4958.TW",  "name": "臻鼎科技",     "name_en": "Zhen Ding Technology",              "tags": ["HDI軟硬板", "FPC", "蘋果供應鏈"]},
            ],
            "CPO光連接": [
                {"symbol": "6919.TW",  "name": "亨泰光",       "name_en": "HGC Fiber Optics",                  "tags": ["CPO光纖連接器", "AI伺服器光互連"]},
                {"symbol": "2345.TW",  "name": "智邦科技",     "name_en": "Accton Technology",                 "tags": ["AI網路交換器", "白牌Switch/CPO受益"]},
                {"symbol": "3081.TWO", "name": "聯亞光電",     "name_en": "Alliance Semiconductor",            "tags": ["雷射磊晶片", "光引擎核心元件"]},
                {"symbol": "6442.TWO", "name": "光聖",         "name_en": "FiberStar",                         "tags": ["光纖被動元件", "CPO連接組件"]},
                {"symbol": "6449.TWO", "name": "申泰",         "name_en": "Shen Tai Co.",                      "tags": ["光收發模組", "SFP/QSFP/400G"]},
                {"symbol": "6207.TWO", "name": "雷科",         "name_en": "LeiKe Technology",                  "tags": ["半導體雷射", "光源元件"]},
                {"symbol": "3152.TWO", "name": "正淩精密",     "name_en": "GigaLane",                          "tags": ["光纖連接器", "高速連接器"]},
                {"symbol": "2338.TW",  "name": "台灣光罩",     "name_en": "Taiwan Mask Corporation",           "tags": ["矽光子光罩", "CPO製程關鍵"]},
            ],
            "科技ETF": [
                {"symbol": "0052.TW",  "name": "富邦科技",     "name_en": "Fubon MSCI Taiwan Technology ETF",  "tags": ["台灣科技50", "電子權值股ETF"]},
            ],
        },

        "資源": {
            "稀土/戰略金屬": [
                {"symbol": "1785.TWO", "name": "光洋科技",     "name_en": "Gallant Metals Co.",                "tags": ["貴金屬/稀土回收", "鉭/鎢材料"]},
                {"symbol": "8390.TWO", "name": "金益鼎",       "name_en": "Chin I Ding Precious Metal",        "tags": ["貴金屬回收交易", "稀有金屬"]},
                {"symbol": "9955.TW",  "name": "佳龍科技",     "name_en": "Jia Long Technology",               "tags": ["稀土戰略金屬通路"]},
            ],
            "黃金": [
                {"symbol": "00635U.TW","name": "元大黃金",      "name_en": "Yuanta Gold ETF",                   "tags": ["黃金期貨ETF", "追蹤COMEX金價"]},
                {"symbol": "00708L.TW","name": "期元大黃金正2", "name_en": "Yuanta Gold 2x Leveraged ETF",     "tags": ["2倍槓桿", "黃金期貨多方"]},
            ],
            "銅礦": [
                {"symbol": "00763U.TW","name": "元大銅期貨",    "name_en": "Yuanta Copper Futures ETF",         "tags": ["銅期貨ETF", "追蹤LME銅價"]},
                {"symbol": "1605.TW",  "name": "華新科技",     "name_en": "Walsin Lihwa",                      "tags": ["電磁線/銅電纜", "電動車線束"]},
                {"symbol": "1609.TW",  "name": "大亞電線電纜", "name_en": "Great Asia Cable & Wire",           "tags": ["低壓電纜", "太陽能用線"]},
                {"symbol": "1608.TW",  "name": "華榮電線電纜", "name_en": "Hua Jung Enterprise",               "tags": ["電力電纜", "高壓配電"]},
                {"symbol": "1618.TW",  "name": "合機電工",     "name_en": "Ho Chi Electric Works",             "tags": ["建築電線電纜"]},
                {"symbol": "1612.TW",  "name": "宏泰電工",     "name_en": "Hung Tay Electric",                 "tags": ["大樓配線", "電線電纜"]},
                {"symbol": "2009.TW",  "name": "第一銅",       "name_en": "Firstcorp",                         "tags": ["銅棒/銅材", "電子用銅"]},
            ],
            "鐵礦鋼鐵": [
                {"symbol": "2002.TW",  "name": "中鋼",         "name_en": "China Steel Corporation",           "tags": ["高爐一貫作業", "熱軋/冷軋鋼"]},
                {"symbol": "2015.TW",  "name": "豐興鋼鐵",     "name_en": "Feng Hsin Steel",                   "tags": ["電弧爐", "鋼筋/型鋼"]},
                {"symbol": "2014.TW",  "name": "中鴻鋼鐵",     "name_en": "Chung Hung Steel",                  "tags": ["冷軋鋼板", "鍍鋅板"]},
                {"symbol": "2006.TW",  "name": "東和鋼鐵",     "name_en": "Tung Ho Steel Enterprise",          "tags": ["電弧爐", "鋼筋/鋼胚"]},
                {"symbol": "2027.TW",  "name": "大成鋼",       "name_en": "Ta Chen Stainless Pipe",            "tags": ["不銹鋼管/板", "鋼材通路"]},
                {"symbol": "2031.TW",  "name": "新光鋼",       "name_en": "Shin Kwang Steel",                  "tags": ["彩色鋼板", "鍍鋅鋼板"]},
                {"symbol": "2023.TW",  "name": "燁輝",         "name_en": "Yieh Phui Enterprise",              "tags": ["不銹鋼冷軋板", "熱軋鋼捲"]},
                {"symbol": "2013.TW",  "name": "中鋼構",       "name_en": "China Steel Structure",             "tags": ["鋼構建築", "橋樑/廠房工程"]},
            ],
        },
    },

    "美國": {
        "半導體": {
            "CPU/GPU產業": {
                "IC設計": [
                    {"symbol": "NVDA",  "name": "輝達",         "name_en": "NVIDIA",                            "tags": ["AI GPU", "CUDA生態"]},
                    {"symbol": "AMD",   "name": "超微",         "name_en": "AMD",                               "tags": ["CPU/GPU", "EPYC伺服器"]},
                    {"symbol": "QCOM",  "name": "高通",         "name_en": "Qualcomm",                          "tags": ["手機AP/5G", "汽車晶片"]},
                    {"symbol": "AVGO",  "name": "博通",         "name_en": "Broadcom",                          "tags": ["網路ASIC", "AI加速器"]},
                    {"symbol": "MRVL",  "name": "邁威爾",       "name_en": "Marvell Technology",                "tags": ["網路/儲存IC", "5G/雲端"]},
                    {"symbol": "MPWR",  "name": "美信整合電源", "name_en": "Monolithic Power Systems",          "tags": ["PMIC", "AI伺服器電源"]},
                    {"symbol": "MTSI",  "name": "MACOM技術",    "name_en": "MACOM Technology Solutions",        "tags": ["GaN-on-Si", "RF/微波"]},
                ],
                "IC代工": [
                    {"symbol": "TSM",   "name": "台積電ADR",    "name_en": "TSMC ADR",                          "tags": ["邏輯代工", "先進製程"]},
                    {"symbol": "GFS",   "name": "格芯",         "name_en": "GlobalFoundries",                   "tags": ["特殊製程代工", "RF/嵌入式"]},
                    {"symbol": "INTC",  "name": "英特爾",       "name_en": "Intel",                             "tags": ["x86 CPU", "IDM/代工"]},
                    {"symbol": "UMC",   "name": "聯電ADR",      "name_en": "UMC ADR",                           "tags": ["成熟製程代工"]},
                ],
                "封裝測試": [
                    {"symbol": "AMKR",  "name": "艾克爾",       "name_en": "Amkor Technology",                  "tags": ["先進封裝", "Fan-out/SiP"]},
                ],
                "系統模組PCB產業": [
                    {"symbol": "MCHP",  "name": "微芯科技",     "name_en": "Microchip Technology",              "tags": ["MCU/FPGA", "嵌入式控制"]},
                    {"symbol": "LSCC",  "name": "萊迪思半導體", "name_en": "Lattice Semiconductor",             "tags": ["低功耗FPGA", "邊緣AI"]},
                    {"symbol": "SLAB",  "name": "矽實驗室",     "name_en": "Silicon Labs",                      "tags": ["IoT MCU", "無線連接"]},
                    {"symbol": "RNECY", "name": "瑞薩電子ADR",  "name_en": "Renesas Electronics ADR",           "tags": ["MCU", "車用/工業"]},
                ],
            },
            "記憶體產業": {
                "DRAM產業": [
                    {"symbol": "MU",    "name": "美光科技",     "name_en": "Micron Technology",                 "tags": ["DRAM/NAND", "HBM"]},
                ],
                "NAND/SSD產業": [
                    {"symbol": "WDC",   "name": "威騰電子",     "name_en": "Western Digital",                   "tags": ["NAND/SSD", "企業儲存"]},
                    {"symbol": "STX",   "name": "希捷科技",     "name_en": "Seagate Technology",                "tags": ["HDD", "企業儲存"]},
                ],
                "NAND控制器/介面": [
                    {"symbol": "MXIC",  "name": "旺宏美國",     "name_en": "Macronix International (OTC)",      "tags": ["NOR Flash", "汽車/工業"]},
                    {"symbol": "SIMO",  "name": "慧榮美國",     "name_en": "Silicon Motion Technology ADR",     "tags": ["NAND主控", "eMMC/UFS"]},
                ],
            },
            "功率半導體產業": {
                "SiC產業": [
                    {"symbol": "WOLF",  "name": "沃夫斯比德",   "name_en": "Wolfspeed",                         "tags": ["SiC基板全球第一", "EV/新能源"]},
                    {"symbol": "ON",    "name": "安森美",       "name_en": "ON Semiconductor",                  "tags": ["SiC MOSFET", "車用功率"]},
                    {"symbol": "STM",   "name": "意法半導體",   "name_en": "STMicroelectronics",                "tags": ["SiC/GaN", "車用MCU"]},
                    {"symbol": "TXN",   "name": "德州儀器",     "name_en": "Texas Instruments",                 "tags": ["類比IC", "PMIC/功率"]},
                ],
                "GaN產業": [
                    {"symbol": "NVTS",  "name": "納維達斯",     "name_en": "Navitas Semiconductor",             "tags": ["GaN IC", "快充/EV"]},
                    {"symbol": "POWI",  "name": "電源整合",     "name_en": "Power Integrations",                "tags": ["電源控制IC", "GaN驅動"]},
                    {"symbol": "GAN",   "name": "GaN Systems",  "name_en": "GAN Systems (via NASDAQ)",          "tags": ["GaN功率元件", "EV充電"]},
                ],
            },
            "材料產業": {
                "光阻": [
                    {"symbol": "ENTG",  "name": "恩特格里斯",   "name_en": "Entegris",                          "tags": ["光阻/製程化學品", "CMP漿料"]},
                    {"symbol": "DD",    "name": "杜邦",         "name_en": "DuPont",                            "tags": ["先進材料", "半導體薄膜"]},
                    {"symbol": "EMN",   "name": "伊士曼化學",   "name_en": "Eastman Chemical",                  "tags": ["特殊化學品", "光學膜"]},
                ],
                "半導體製程相關氣體": [
                    {"symbol": "APD",   "name": "氣體產品",     "name_en": "Air Products and Chemicals",        "tags": ["工業氣體", "H₂/特殊氣"]},
                    {"symbol": "LIN",   "name": "林德集團",     "name_en": "Linde plc",                         "tags": ["工業氣體全球第一", "製程氣體"]},
                    {"symbol": "AIQUY", "name": "法液空ADR",    "name_en": "Air Liquide ADR",                   "tags": ["工業氣體", "半導體特氣"]},
                ],
                "半導體製程相關液體": [
                    {"symbol": "ENTG",  "name": "恩特格里斯",   "name_en": "Entegris",                          "tags": ["CMP漿料", "製程液體"]},
                    {"symbol": "MKSI",  "name": "MKS儀器",      "name_en": "MKS Instruments",                   "tags": ["製程控制儀器", "氣體管控"]},
                    {"symbol": "LRCX",  "name": "科林研發",     "name_en": "Lam Research",                      "tags": ["蝕刻設備", "沉積設備"]},
                ],
            },
            "磊晶產業": {
                "Si晶圓": [
                    {"symbol": "SUMCF", "name": "SUMCO",        "name_en": "Sumco Corp (OTC)",                  "tags": ["矽晶圓", "日本全球第二"]},
                    {"symbol": "AMAT",  "name": "應用材料",     "name_en": "Applied Materials",                 "tags": ["CVD/PVD設備", "磊晶設備"]},
                    {"symbol": "KLAC",  "name": "科磊",         "name_en": "KLA Corporation",                   "tags": ["良率管理/檢測", "製程控制"]},
                ],
                "SiC晶圓": [
                    {"symbol": "WOLF",  "name": "沃夫斯比德",   "name_en": "Wolfspeed",                         "tags": ["SiC基板全球第一", "EV/新能源"]},
                    {"symbol": "ON",    "name": "安森美",       "name_en": "ON Semiconductor",                  "tags": ["SiC MOSFET", "車用功率"]},
                ],
                "GaN晶圓": [
                    {"symbol": "MTSI",  "name": "MACOM技術",    "name_en": "MACOM Technology",                  "tags": ["GaN-on-Si", "射頻/微波"]},
                    {"symbol": "NVTS",  "name": "納維達斯",     "name_en": "Navitas Semiconductor",             "tags": ["GaN IC", "快充/EV"]},
                ],
            },
            "半導體ETF": [
                {"symbol": "SMH",   "name": "半導體ETF",        "name_en": "VanEck Semiconductor ETF",          "tags": ["市值加權", "台積電/輝達高比重"]},
                {"symbol": "SOXX",  "name": "iShares半導體",    "name_en": "iShares Semiconductor ETF",         "tags": ["費城半導體指數", "30檔"]},
                {"symbol": "SOXL",  "name": "3倍半導體ETF",     "name_en": "Direxion Semiconductor 3x Bull",   "tags": ["3倍槓桿", "高波動"]},
                {"symbol": "PSI",   "name": "景順半導體ETF",    "name_en": "Invesco Dynamic Semiconductors",   "tags": ["動態選股", "美國半導體"]},
            ],
        },
        "資源": {
            "稀土": [
                {"symbol": "MP",    "name": "MP材料",           "name_en": "MP Materials",                      "tags": ["美國最大稀土礦", "Mountain Pass"]},
                {"symbol": "REMX",  "name": "稀土ETF",          "name_en": "VanEck Rare Earth & Strategic Metals","tags": ["稀土/戰略金屬ETF"]},
                {"symbol": "LYSDY", "name": "萊納斯稀土ADR",    "name_en": "Lynas Rare Earths ADR",             "tags": ["澳洲最大稀土", "非中國供應"]},
                {"symbol": "NB",    "name": "諾科特礦業",       "name_en": "NioCorp Developments",              "tags": ["鈮/鈧/鈦", "戰略金屬"]},
            ],
            "黃金": [
                {"symbol": "GLD",   "name": "黃金ETF",          "name_en": "SPDR Gold ETF",                     "tags": ["實物黃金ETF", "最大規模"]},
                {"symbol": "GDX",   "name": "金礦ETF",          "name_en": "VanEck Gold Miners ETF",            "tags": ["金礦股ETF", "大型礦商"]},
                {"symbol": "GDXJ",  "name": "小型金礦ETF",      "name_en": "VanEck Junior Gold Miners",         "tags": ["中小型金礦", "高成長潛力"]},
                {"symbol": "NEM",   "name": "紐蒙特",           "name_en": "Newmont Corporation",               "tags": ["全球最大金礦商", "低成本"]},
                {"symbol": "GOLD",  "name": "巴里克黃金",       "name_en": "Barrick Gold",                      "tags": ["全球第二金礦", "銅金並進"]},
                {"symbol": "AEM",   "name": "阿哥尼科鷹",       "name_en": "Agnico Eagle Mines",                "tags": ["加拿大優質金礦", "低AISC"]},
                {"symbol": "KGC",   "name": "金羅斯黃金",       "name_en": "Kinross Gold",                      "tags": ["中型金礦商", "美洲/非洲礦"]},
            ],
            "銅礦": [
                {"symbol": "FCX",   "name": "自由港麥克莫蘭",   "name_en": "Freeport-McMoRan",                  "tags": ["全球最大銅礦商", "印尼Grasberg"]},
                {"symbol": "SCCO",  "name": "南方銅業",         "name_en": "Southern Copper",                   "tags": ["低成本銅礦", "墨西哥/秘魯"]},
                {"symbol": "COPX",  "name": "銅礦ETF",          "name_en": "Global X Copper Miners ETF",        "tags": ["銅礦股ETF", "全球布局"]},
                {"symbol": "TECK",  "name": "特克資源",         "name_en": "Teck Resources",                    "tags": ["銅鋅礦", "加拿大"]},
                {"symbol": "HBM",   "name": "哈德灣礦業",       "name_en": "Hudbay Minerals",                   "tags": ["銅金礦", "加拿大/秘魯"]},
            ],
            "鐵礦鋼鐵": [
                {"symbol": "NUE",   "name": "紐柯",             "name_en": "Nucor Corporation",                 "tags": ["電弧爐鋼鐵", "美國最大"]},
                {"symbol": "CLF",   "name": "克里夫蘭崖",       "name_en": "Cleveland-Cliffs",                  "tags": ["鐵礦/鋼鐵一體", "汽車用鋼"]},
                {"symbol": "VALE",  "name": "淡水河谷",         "name_en": "Vale SA",                           "tags": ["全球最大鐵礦商", "巴西"]},
                {"symbol": "RIO",   "name": "力拓",             "name_en": "Rio Tinto",                         "tags": ["鐵礦/銅/鋁", "澳洲/全球"]},
                {"symbol": "BHP",   "name": "必和必拓",         "name_en": "BHP Group",                         "tags": ["全球最大礦商", "鐵礦/銅/鎳"]},
                {"symbol": "MT",    "name": "安賽樂米塔爾",     "name_en": "ArcelorMittal",                     "tags": ["全球最大鋼鐵", "歐美亞布局"]},
                {"symbol": "X",     "name": "美國鋼鐵",         "name_en": "US Steel",                          "tags": ["美國鋼鐵", "電弧爐轉型"]},
            ],
        },
    },
}

# Major indices for the top bar
MARKET_INDICES = [
    {"symbol": "^TWII",  "name": "台灣加權",  "name_en": "TAIEX"},
    {"symbol": "^GSPC",  "name": "S&P 500",   "name_en": "S&P 500"},
    {"symbol": "^IXIC",  "name": "那斯達克",  "name_en": "NASDAQ"},
    {"symbol": "^DJI",   "name": "道瓊",      "name_en": "Dow Jones"},
    {"symbol": "^SOX",   "name": "費城半導體", "name_en": "Philadelphia SOX"},
    {"symbol": "GC=F",   "name": "黃金期貨",  "name_en": "Gold Futures"},
    {"symbol": "HG=F",   "name": "銅期貨",    "name_en": "Copper Futures"},
]
