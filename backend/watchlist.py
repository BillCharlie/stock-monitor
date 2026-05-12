# Watchlist — hierarchy: 地區 > 産業 > 細分類 (> 四級分類)
# Leaf values are lists of {symbol, name, name_en}
# Branch values are dicts of sub-categories

WATCHLIST = {
    "台灣": {
        "半導體": {
            "晶圓代工": [
                {"symbol": "2330.TW",  "name": "台積電",       "name_en": "TSMC"},
                {"symbol": "2303.TW",  "name": "聯電",         "name_en": "UMC"},
                {"symbol": "5347.TW",  "name": "世界先進",     "name_en": "Vanguard International Semiconductor"},
                {"symbol": "6770.TW",  "name": "力積電",       "name_en": "Powerchip Semiconductor (PSMC)"},
                {"symbol": "6789.TW",  "name": "采鈺科技",     "name_en": "VisEra Technologies"},
                {"symbol": "8028.TW",  "name": "昇陽半導體",   "name_en": "Eris Technology Corp"},
            ],
            "IC設計": [
                {"symbol": "2454.TW",  "name": "聯發科技",     "name_en": "MediaTek"},
                {"symbol": "3034.TW",  "name": "聯詠科技",     "name_en": "Novatek Microelectronics"},
                {"symbol": "2379.TW",  "name": "瑞昱半導體",   "name_en": "Realtek Semiconductor"},
                {"symbol": "3443.TW",  "name": "創意電子",     "name_en": "Global Unichip (GUC)"},
                {"symbol": "3035.TW",  "name": "智原科技",     "name_en": "Faraday Technology"},
                {"symbol": "5274.TW",  "name": "信驊科技",     "name_en": "Aspeed Technology"},
                {"symbol": "3529.TW",  "name": "力旺電子",     "name_en": "eMemory Technology"},
                {"symbol": "3661.TW",  "name": "世芯-KY",      "name_en": "Alchip Technologies"},
                {"symbol": "8016.TW",  "name": "矽創電子",     "name_en": "Sitronix Technology"},
                {"symbol": "4966.TW",  "name": "譜瑞-KY",      "name_en": "Parade Technologies"},
                {"symbol": "6756.TW",  "name": "威鋒電子",     "name_en": "VIA Labs"},
                {"symbol": "6415.TW",  "name": "矽力-KY",      "name_en": "Silergy Corp"},
                {"symbol": "6202.TW",  "name": "盛群半導體",   "name_en": "Holtek Semiconductor"},
                {"symbol": "6643.TW",  "name": "M31科技",      "name_en": "M31 Technology Corp"},
                {"symbol": "3227.TW",  "name": "原相科技",     "name_en": "PixArt Imaging"},
                {"symbol": "2458.TW",  "name": "義隆電子",     "name_en": "ELAN Microelectronics"},
                {"symbol": "6531.TW",  "name": "愛普科技",     "name_en": "Apex Technologies"},
            ],
            "記憶體": [
                {"symbol": "2408.TW",  "name": "南亞科技",     "name_en": "Nanya Technology"},
                {"symbol": "2337.TW",  "name": "旺宏電子",     "name_en": "Macronix International"},
                {"symbol": "2344.TW",  "name": "華邦電子",     "name_en": "Winbond Electronics"},
                {"symbol": "8299.TW",  "name": "群聯電子",     "name_en": "Phison Electronics"},
                {"symbol": "6286.TW",  "name": "慧榮科技",     "name_en": "Silicon Motion"},
                {"symbol": "4919.TW",  "name": "新唐科技",     "name_en": "Nuvoton Technology"},
                {"symbol": "3260.TW",  "name": "威剛科技",     "name_en": "ADATA Technology"},
                {"symbol": "2451.TW",  "name": "創見資訊",     "name_en": "Transcend Information"},
                {"symbol": "4967.TW",  "name": "十銓科技",     "name_en": "Team Group"},
            ],
            "封裝測試": {
                "封測廠": [
                    {"symbol": "2311.TW",  "name": "日月光投控", "name_en": "ASE Technology Holding"},
                    {"symbol": "6239.TW",  "name": "力成科技",   "name_en": "Powertech Technology"},
                    {"symbol": "2449.TW",  "name": "京元電子",   "name_en": "King Yuan Electronics"},
                    {"symbol": "3264.TW",  "name": "欣銓科技",   "name_en": "Chipbond Technology"},
                    {"symbol": "6257.TW",  "name": "矽格半導體", "name_en": "Sigurd Microelectronics"},
                    {"symbol": "2329.TW",  "name": "華泰電子",   "name_en": "HMC Hwa Mei Corporation"},
                    {"symbol": "8110.TW",  "name": "華東科技",   "name_en": "Hua Tong Electronic"},
                ],
                "探針卡": [
                    {"symbol": "6510.TW",  "name": "精測電子",   "name_en": "Chunghwa Precision Test Tech"},
                    {"symbol": "6223.TW",  "name": "旺矽科技",   "name_en": "MJC Probe"},
                ],
                "IC載板": [
                    {"symbol": "3189.TW",  "name": "景碩科技",   "name_en": "Kinsus Interconnect Technology"},
                    {"symbol": "3037.TW",  "name": "欣興電子",   "name_en": "Unimicron Technology"},
                    {"symbol": "8046.TW",  "name": "南電",        "name_en": "Nan Ya PCB"},
                ],
            },
            "功率元件": [
                {"symbol": "3707.TW",  "name": "漢磊科技",     "name_en": "Han Lei Technology (SiC/GaN)"},
                {"symbol": "8255.TW",  "name": "朋程科技",     "name_en": "Anpec Electronics"},
                {"symbol": "2481.TW",  "name": "強茂",         "name_en": "General Semiconductor"},
                {"symbol": "5425.TW",  "name": "台半",         "name_en": "Taiwan Semiconductor Co."},
                {"symbol": "3105.TW",  "name": "穩懋半導體",   "name_en": "WIN Semiconductors (GaN)"},
                {"symbol": "8086.TW",  "name": "宏捷科技",     "name_en": "Advanced Wireless Semiconductor"},
                {"symbol": "5299.TW",  "name": "杰力科技",     "name_en": "Jetek Semiconductor"},
                {"symbol": "3675.TW",  "name": "德微科技",     "name_en": "De Wei Technology"},
                {"symbol": "2342.TW",  "name": "茂矽電子",     "name_en": "MoselVitelic"},
                {"symbol": "3317.TW",  "name": "尼克森微",     "name_en": "Niko Semiconductor"},
                {"symbol": "2455.TW",  "name": "全新光電",     "name_en": "Advanced Photonics"},
                {"symbol": "6616.TW",  "name": "特昇科技",     "name_en": "Teresic Technology (SiC)"},
                {"symbol": "6104.TW",  "name": "創杰科技",     "name_en": "Carsem Semiconductor (GaN)"},
                {"symbol": "2448.TW",  "name": "晶元光電",     "name_en": "Epistar"},
            ],
            "材料": [
                # 晶圓 / 基板
                {"symbol": "6488.TW",  "name": "環球晶圓",     "name_en": "GlobalWafers"},
                {"symbol": "6182.TW",  "name": "合晶科技",     "name_en": "Sino-American Silicon"},
                {"symbol": "3532.TW",  "name": "台勝科",       "name_en": "Episil Technologies"},
                {"symbol": "3016.TW",  "name": "嘉晶電子",     "name_en": "Episil-Precision"},
                # 化學品
                {"symbol": "1711.TW",  "name": "永光化學",     "name_en": "Ever Light Chemical"},
                {"symbol": "1717.TW",  "name": "長興材料",     "name_en": "Chang Chun Group"},
                {"symbol": "4552.TW",  "name": "力拓科技",     "name_en": "Leatec Fine Ceramics"},
                {"symbol": "4503.TW",  "name": "金洲精密",     "name_en": "Chin Chou Precision"},
                {"symbol": "1323.TW",  "name": "永裕",         "name_en": "Yung Yu Chemical"},
                {"symbol": "1760.TW",  "name": "寶一化學",     "name_en": "Pac-Tech Chemical"},
                {"symbol": "6646.TW",  "name": "日揚科技",     "name_en": "Scientech (process)"},
                # 精密材料 / 研磨 / 耗材
                {"symbol": "1560.TW",  "name": "中砂",         "name_en": "Kinik Company"},
                {"symbol": "4768.TW",  "name": "晶呈科技",     "name_en": "Cryscore Optoelectronic"},
                {"symbol": "4772.TW",  "name": "台特化",       "name_en": "Taiwan Speciality Chemicals"},
                {"symbol": "5434.TW",  "name": "崇越科技",     "name_en": "Topco Scientific"},
                {"symbol": "3680.TW",  "name": "家登精密",     "name_en": "Gudeng Precision Industrial"},
            ],
            "設備": [
                {"symbol": "2404.TW",  "name": "漢唐集成",     "name_en": "Han Tang Systems"},
                {"symbol": "6196.TW",  "name": "帆宣系統",     "name_en": "Marketech International"},
                {"symbol": "6139.TW",  "name": "亞翔工程",     "name_en": "Asia Allied Infrastructure"},
                {"symbol": "5536.TW",  "name": "聖暉企業",     "name_en": "Summit Grand Enterprise"},
                {"symbol": "6691.TW",  "name": "洋基工程",     "name_en": "Yankee Engineering Corp"},
                {"symbol": "3131.TW",  "name": "弘塑科技",     "name_en": "Hung Hing Precision Technology"},
                {"symbol": "3583.TW",  "name": "辛耘企業",     "name_en": "Scientech Corp"},
                {"symbol": "3413.TW",  "name": "京鼎精密",     "name_en": "Kinergy Advanced Technology"},
                {"symbol": "6187.TW",  "name": "萬潤科技",     "name_en": "Wan Jung Technology"},
                {"symbol": "3167.TW",  "name": "大量電子",     "name_en": "Daliwa Electronics"},
            ],
            "半導體ETF": [
                {"symbol": "00891.TW", "name": "中信關鍵半導體","name_en": "CTBC Key Semiconductor ETF"},
                {"symbol": "00892.TW", "name": "富邦台灣半導體","name_en": "Fubon Taiwan Semiconductor ETF"},
                {"symbol": "00904.TW", "name": "新光台灣半導體","name_en": "Shin Kong TW Semiconductor ETF"},
                {"symbol": "00913.TW", "name": "半導體科技ETF", "name_en": "Semiconductor Tech ETF"},
                {"symbol": "00927.TW", "name": "群益半導體收益","name_en": "Capital Semiconductor Income ETF"},
                {"symbol": "00947.TW", "name": "元大AI半導體",  "name_en": "Yuanta Global AI Semiconductor ETF"},
            ],
        },

        "科技系統廠": {
            "EMS/AI服務器": [
                {"symbol": "2317.TW",  "name": "鴻海精密",     "name_en": "Hon Hai Precision (Foxconn)"},
                {"symbol": "2382.TW",  "name": "廣達電腦",     "name_en": "Quanta Computer"},
                {"symbol": "3231.TW",  "name": "緯創資通",     "name_en": "Wistron Corporation"},
                {"symbol": "6669.TW",  "name": "緯穎科技",     "name_en": "Wiwynn Corporation"},
                {"symbol": "2356.TW",  "name": "英業達",       "name_en": "Inventec Corporation"},
                {"symbol": "2324.TW",  "name": "仁寶電腦",     "name_en": "Compal Electronics"},
                {"symbol": "4938.TW",  "name": "和碩聯合科技", "name_en": "Pegatron Corporation"},
                {"symbol": "3706.TW",  "name": "神達電腦",     "name_en": "MiTAC Holdings"},
            ],
            "品牌PC/主板/電競": [
                {"symbol": "2357.TW",  "name": "華碩電腦",     "name_en": "ASUSTeK Computer"},
                {"symbol": "2353.TW",  "name": "宏碁",         "name_en": "Acer Inc."},
                {"symbol": "2376.TW",  "name": "技嘉科技",     "name_en": "Gigabyte Technology"},
                {"symbol": "2377.TW",  "name": "微星科技",     "name_en": "MSI (Micro-Star International)"},
            ],
            "工業電腦/邊緣運算": [
                {"symbol": "2395.TW",  "name": "研華科技",     "name_en": "Advantech Co."},
                {"symbol": "2352.TW",  "name": "佳世達科技",   "name_en": "Qisda Corporation"},
                {"symbol": "3706.TW",  "name": "神達電腦",     "name_en": "MiTAC Holdings"},
            ],
            "電源/散熱/機電": [
                {"symbol": "2308.TW",  "name": "台達電子",     "name_en": "Delta Electronics"},
                {"symbol": "2301.TW",  "name": "光寶科技",     "name_en": "Lite-On Technology"},
                {"symbol": "8210.TW",  "name": "勤誠興業",     "name_en": "Chenbro Micom"},
                {"symbol": "3017.TW",  "name": "奇鋐科技",     "name_en": "Asia Vital Components (AVC)"},
                {"symbol": "3324.TW",  "name": "雙鴻科技",     "name_en": "Shuang Hong Technology"},
            ],
            "科技ETF": [
                {"symbol": "0052.TW",  "name": "富邦科技",     "name_en": "Fubon MSCI Taiwan Technology ETF"},
            ],
        },

        "資源": {
            "稀土/戰略金屬": [
                {"symbol": "1785.TW",  "name": "光洋科技",     "name_en": "Gallant Metals Co."},
                {"symbol": "8390.TW",  "name": "金益鼎",       "name_en": "Chin I Ding Precious Metal"},
                {"symbol": "9955.TW",  "name": "佳龍科技",     "name_en": "Jia Long Technology"},
            ],
            "黃金": [
                {"symbol": "00635U.TW","name": "元大黃金",      "name_en": "Yuanta Gold ETF"},
                {"symbol": "00708L.TW","name": "期元大黃金正2", "name_en": "Yuanta Gold 2x Leveraged ETF"},
            ],
            "銅礦": [
                {"symbol": "00763U.TW","name": "元大銅期貨",    "name_en": "Yuanta Copper Futures ETF"},
                {"symbol": "1605.TW",  "name": "華新科技",     "name_en": "Walsin Lihwa (Copper Cable)"},
                {"symbol": "1609.TW",  "name": "大亞電線電纜", "name_en": "Great Asia Cable & Wire"},
                {"symbol": "1608.TW",  "name": "華榮電線電纜", "name_en": "Hua Jung Enterprise"},
                {"symbol": "1618.TW",  "name": "合機電工",     "name_en": "Ho Chi Electric Works"},
                {"symbol": "1612.TW",  "name": "宏泰電工",     "name_en": "Hung Tay Electric"},
                {"symbol": "2009.TW",  "name": "第一銅",       "name_en": "Firstcorp"},
            ],
            "鐵礦鋼鐵": [
                {"symbol": "2002.TW",  "name": "中鋼",         "name_en": "China Steel Corporation"},
                {"symbol": "2015.TW",  "name": "豐興鋼鐵",     "name_en": "Feng Hsin Steel"},
                {"symbol": "2014.TW",  "name": "中鴻鋼鐵",     "name_en": "Chung Hung Steel"},
                {"symbol": "2006.TW",  "name": "東和鋼鐵",     "name_en": "Tung Ho Steel Enterprise"},
                {"symbol": "2027.TW",  "name": "大成鋼",       "name_en": "Ta Chen Stainless Pipe"},
                {"symbol": "2031.TW",  "name": "新光鋼",       "name_en": "Shin Kwang Steel"},
                {"symbol": "2023.TW",  "name": "燁輝",         "name_en": "Yieh Phui Enterprise"},
                {"symbol": "2013.TW",  "name": "中鋼構",       "name_en": "China Steel Structure"},
            ],
        },
    },

    "美國": {
        "半導體": {
            "CPU/GPU產業": {
                "IC設計": [
                    {"symbol": "NVDA",  "name": "輝達",         "name_en": "NVIDIA"},
                    {"symbol": "AMD",   "name": "超微",         "name_en": "AMD"},
                    {"symbol": "QCOM",  "name": "高通",         "name_en": "Qualcomm"},
                    {"symbol": "AVGO",  "name": "博通",         "name_en": "Broadcom"},
                    {"symbol": "MRVL",  "name": "邁威爾",       "name_en": "Marvell Technology"},
                    {"symbol": "MPWR",  "name": "美信整合電源", "name_en": "Monolithic Power Systems"},
                    {"symbol": "MTSI",  "name": "MACOM技術",    "name_en": "MACOM Technology Solutions"},
                ],
                "IC代工": [
                    {"symbol": "TSM",   "name": "台積電ADR",    "name_en": "TSMC ADR"},
                    {"symbol": "GFS",   "name": "格芯",         "name_en": "GlobalFoundries"},
                    {"symbol": "INTC",  "name": "英特爾",       "name_en": "Intel"},
                    {"symbol": "UMC",   "name": "聯電ADR",      "name_en": "UMC ADR"},
                ],
                "封裝測試": [
                    {"symbol": "AMKR",  "name": "艾克爾",       "name_en": "Amkor Technology"},
                ],
                "系統模組PCB產業": [
                    {"symbol": "MCHP",  "name": "微芯科技",     "name_en": "Microchip Technology (MCU+Flash)"},
                    {"symbol": "LSCC",  "name": "萊迪思半導體", "name_en": "Lattice Semiconductor (FPGA/PCB)"},
                    {"symbol": "SLAB",  "name": "矽實驗室",     "name_en": "Silicon Labs (MCU/System)"},
                    {"symbol": "RNECY", "name": "瑞薩電子ADR",  "name_en": "Renesas Electronics ADR (MCU)"},
                ],
            },
            "記憶體產業": {
                "DRAM產業": [
                    {"symbol": "MU",    "name": "美光科技",     "name_en": "Micron Technology (DRAM+NAND)"},
                ],
                "NAND/SSD產業": [
                    {"symbol": "WDC",   "name": "威騰電子",     "name_en": "Western Digital (NAND/SSD)"},
                    {"symbol": "STX",   "name": "希捷科技",     "name_en": "Seagate Technology (HDD/SSD)"},
                ],
                "NAND控制器/介面": [
                    {"symbol": "MXIC",  "name": "旺宏美國",     "name_en": "Macronix International (OTC)"},
                    {"symbol": "SIMO",  "name": "慧榮美國",     "name_en": "Silicon Motion Technology ADR"},
                ],
            },
            "功率半導體產業": {
                "SiC產業": [
                    {"symbol": "WOLF",  "name": "沃夫斯比德",   "name_en": "Wolfspeed"},
                    {"symbol": "ON",    "name": "安森美",       "name_en": "ON Semiconductor"},
                    {"symbol": "STM",   "name": "意法半導體",   "name_en": "STMicroelectronics"},
                    {"symbol": "TXN",   "name": "德州儀器",     "name_en": "Texas Instruments"},
                ],
                "GaN產業": [
                    {"symbol": "NVTS",  "name": "納維達斯",     "name_en": "Navitas Semiconductor"},
                    {"symbol": "POWI",  "name": "電源整合",     "name_en": "Power Integrations"},
                    {"symbol": "GAN",   "name": "GaN Systems",  "name_en": "GAN Systems (via NASDAQ)"},
                ],
            },
            "材料產業": {
                "光阻": [
                    {"symbol": "ENTG",  "name": "恩特格里斯",   "name_en": "Entegris (photochemicals)"},
                    {"symbol": "DD",    "name": "杜邦",         "name_en": "DuPont (advanced materials)"},
                    {"symbol": "EMN",   "name": "伊士曼化學",   "name_en": "Eastman Chemical"},
                ],
                "半導體製程相關氣體": [
                    {"symbol": "APD",   "name": "氣體產品",     "name_en": "Air Products and Chemicals"},
                    {"symbol": "LIN",   "name": "林德集團",     "name_en": "Linde plc"},
                    {"symbol": "AIQUY", "name": "法液空ADR",    "name_en": "Air Liquide ADR"},
                ],
                "半導體製程相關液體": [
                    {"symbol": "ENTG",  "name": "恩特格里斯",   "name_en": "Entegris (CMP slurry, chemicals)"},
                    {"symbol": "MKSI",  "name": "MKS儀器",      "name_en": "MKS Instruments"},
                    {"symbol": "LRCX",  "name": "科林研發",     "name_en": "Lam Research"},
                ],
            },
            "磊晶產業": {
                "Si晶圓": [
                    {"symbol": "SUMCF", "name": "SUMCO",        "name_en": "Sumco Corp (OTC)"},
                    {"symbol": "AMAT",  "name": "應用材料",     "name_en": "Applied Materials (epi equip)"},
                    {"symbol": "KLAC",  "name": "科磊",         "name_en": "KLA Corporation"},
                ],
                "SiC晶圓": [
                    {"symbol": "WOLF",  "name": "沃夫斯比德",   "name_en": "Wolfspeed (SiC substrates, world #1)"},
                    {"symbol": "ON",    "name": "安森美",       "name_en": "ON Semiconductor (SiC devices)"},
                ],
                "GaN晶圓": [
                    {"symbol": "MTSI",  "name": "MACOM技術",    "name_en": "MACOM Technology (GaN-on-Si)"},
                    {"symbol": "NVTS",  "name": "納維達斯",     "name_en": "Navitas Semiconductor (GaN ICs)"},
                ],
            },
            "半導體ETF": [
                {"symbol": "SMH",   "name": "半導體ETF",        "name_en": "VanEck Semiconductor ETF"},
                {"symbol": "SOXX",  "name": "iShares半導體",    "name_en": "iShares Semiconductor ETF"},
                {"symbol": "SOXL",  "name": "3倍半導體ETF",     "name_en": "Direxion Semiconductor 3x Bull"},
                {"symbol": "PSI",   "name": "景順半導體ETF",    "name_en": "Invesco Dynamic Semiconductors"},
            ],
        },
        "資源": {
            "稀土": [
                {"symbol": "MP",    "name": "MP材料",           "name_en": "MP Materials"},
                {"symbol": "REMX",  "name": "稀土ETF",          "name_en": "VanEck Rare Earth & Strategic Metals"},
                {"symbol": "LYSDY", "name": "萊納斯稀土ADR",    "name_en": "Lynas Rare Earths ADR"},
                {"symbol": "NB",    "name": "諾科特礦業",       "name_en": "NioCorp Developments"},
            ],
            "黃金": [
                {"symbol": "GLD",   "name": "黃金ETF",          "name_en": "SPDR Gold ETF"},
                {"symbol": "GDX",   "name": "金礦ETF",          "name_en": "VanEck Gold Miners ETF"},
                {"symbol": "GDXJ",  "name": "小型金礦ETF",      "name_en": "VanEck Junior Gold Miners"},
                {"symbol": "NEM",   "name": "紐蒙特",           "name_en": "Newmont Corporation"},
                {"symbol": "GOLD",  "name": "巴里克黃金",       "name_en": "Barrick Gold"},
                {"symbol": "AEM",   "name": "阿哥尼科鷹",       "name_en": "Agnico Eagle Mines"},
                {"symbol": "KGC",   "name": "金羅斯黃金",       "name_en": "Kinross Gold"},
            ],
            "銅礦": [
                {"symbol": "FCX",   "name": "自由港麥克莫蘭",   "name_en": "Freeport-McMoRan"},
                {"symbol": "SCCO",  "name": "南方銅業",         "name_en": "Southern Copper"},
                {"symbol": "COPX",  "name": "銅礦ETF",          "name_en": "Global X Copper Miners ETF"},
                {"symbol": "TECK",  "name": "特克資源",         "name_en": "Teck Resources"},
                {"symbol": "HBM",   "name": "哈德灣礦業",       "name_en": "Hudbay Minerals"},
            ],
            "鐵礦鋼鐵": [
                {"symbol": "NUE",   "name": "紐柯",             "name_en": "Nucor Corporation"},
                {"symbol": "CLF",   "name": "克里夫蘭崖",       "name_en": "Cleveland-Cliffs"},
                {"symbol": "VALE",  "name": "淡水河谷",         "name_en": "Vale SA"},
                {"symbol": "RIO",   "name": "力拓",             "name_en": "Rio Tinto"},
                {"symbol": "BHP",   "name": "必和必拓",         "name_en": "BHP Group"},
                {"symbol": "MT",    "name": "安賽樂米塔爾",     "name_en": "ArcelorMittal"},
                {"symbol": "X",     "name": "美國鋼鐵",         "name_en": "US Steel"},
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
