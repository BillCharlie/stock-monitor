# Watchlist — hierarchy: 地區 > 産業 > 細分類 (> 四級分類)
# Leaf values are lists of {symbol, name, name_en}
# Branch values are dicts of sub-categories

WATCHLIST = {
    "台灣": {
        "半導體": {
            "CPU/GPU產業": {
                "IC設計": [
                    {"symbol": "2454.TW", "name": "聯發科技",   "name_en": "MediaTek"},
                    {"symbol": "3034.TW", "name": "聯詠科技",   "name_en": "Novatek Microelectronics"},
                    {"symbol": "2379.TW", "name": "瑞昱半導體", "name_en": "Realtek Semiconductor"},
                    {"symbol": "3443.TW", "name": "創意電子",   "name_en": "Global Unichip (GUC)"},
                    {"symbol": "3035.TW", "name": "智原科技",   "name_en": "Faraday Technology"},
                    {"symbol": "5274.TW", "name": "信驊科技",   "name_en": "Aspeed Technology"},
                    {"symbol": "6770.TW", "name": "力旺電子",   "name_en": "eMemory Technology"},
                ],
                "IC代工": [
                    {"symbol": "2330.TW", "name": "台積電",     "name_en": "TSMC"},
                    {"symbol": "2303.TW", "name": "聯電",       "name_en": "UMC"},
                    {"symbol": "5347.TW", "name": "世界先進",   "name_en": "Vanguard International Semiconductor"},
                ],
                "封裝測試": [
                    {"symbol": "2311.TW", "name": "日月光投控", "name_en": "ASE Technology Holding"},
                    {"symbol": "6239.TW", "name": "力成科技",   "name_en": "Powertech Technology"},
                    {"symbol": "2449.TW", "name": "京元電子",   "name_en": "King Yuan Electronics"},
                    {"symbol": "8046.TW", "name": "南電",       "name_en": "Nan Ya PCB"},
                ],
                "系統模組PCB產業": [
                    {"symbol": "2408.TW", "name": "南亞科技",   "name_en": "Nanya Technology"},
                    {"symbol": "2344.TW", "name": "華邦電子",   "name_en": "Winbond Electronics"},
                    {"symbol": "2337.TW", "name": "旺宏電子",   "name_en": "Macronix International"},
                    {"symbol": "4919.TW", "name": "新唐科技",   "name_en": "Nuvoton Technology"},
                ],
            },
            "記憶體產業": {
                "DRAM產業": [
                    {"symbol": "2408.TW", "name": "南亞科技",   "name_en": "Nanya Technology (DRAM)"},
                ],
                "NOR Flash/eFlash": [
                    {"symbol": "2337.TW", "name": "旺宏電子",   "name_en": "Macronix International (NOR Flash)"},
                    {"symbol": "2344.TW", "name": "華邦電子",   "name_en": "Winbond Electronics (NOR/NAND Flash)"},
                ],
                "NAND/儲存控制": [
                    {"symbol": "8299.TW", "name": "群聯電子",   "name_en": "Phison Electronics (NAND Controller)"},
                    {"symbol": "6286.TW", "name": "慧榮科技",   "name_en": "Silicon Motion (NAND Controller)"},
                ],
                "嵌入式記憶體/MCU": [
                    {"symbol": "4919.TW", "name": "新唐科技",   "name_en": "Nuvoton Technology (MCU+Flash)"},
                ],
            },
            "功率半導體產業": {
                "SiC產業": [
                    {"symbol": "3707.TW", "name": "漢磊科技",   "name_en": "Han Lei Technology"},
                    {"symbol": "8255.TW", "name": "朋程科技",   "name_en": "Anpec Electronics"},
                    {"symbol": "2481.TW", "name": "強茂",       "name_en": "General Semiconductor"},
                    {"symbol": "5425.TW", "name": "台半",       "name_en": "Taiwan Semiconductor Co."},
                ],
                "GaN產業": [
                    {"symbol": "3105.TW", "name": "穩懋半導體", "name_en": "WIN Semiconductors"},
                    {"symbol": "8086.TW", "name": "宏捷科技",   "name_en": "Advanced Wireless Semiconductor (AWSC)"},
                    {"symbol": "5299.TW", "name": "杰力科技",   "name_en": "Jetek Semiconductor"},
                ],
            },
            "材料產業": {
                "光阻": [
                    {"symbol": "1711.TW", "name": "永光化學",   "name_en": "Ever Light Chemical"},
                    {"symbol": "1717.TW", "name": "長興材料",   "name_en": "Chang Chun Plastics"},
                    {"symbol": "4552.TW", "name": "力拓科技",   "name_en": "Leatec Fine Ceramics"},
                ],
                "半導體製程相關氣體": [
                    {"symbol": "4503.TW", "name": "金洲精密",   "name_en": "Chin Chou Precision"},
                    {"symbol": "1323.TW", "name": "永裕",       "name_en": "Yung Yu Chemical"},
                ],
                "半導體製程相關液體": [
                    {"symbol": "1760.TW", "name": "寶一化學",   "name_en": "Pac-Tech Chemical"},
                    {"symbol": "6646.TW", "name": "日揚科技",   "name_en": "Scientech"},
                    {"symbol": "3016.TW", "name": "嘉晶電子",   "name_en": "Episil-Precision"},
                ],
            },
            "磊晶產業": {
                "Si晶圓": [
                    {"symbol": "6488.TW", "name": "環球晶圓",   "name_en": "GlobalWafers"},
                    {"symbol": "6182.TW", "name": "合晶科技",   "name_en": "Sino-American Silicon Products"},
                    {"symbol": "3532.TW", "name": "台勝科",     "name_en": "Episil Technologies"},
                ],
                "SiC晶圓": [
                    {"symbol": "3707.TW", "name": "漢磊科技",   "name_en": "Han Lei Technology (SiC Epi)"},
                    {"symbol": "6616.TW", "name": "特昇科技",   "name_en": "Teresic Technology"},
                ],
                "GaN晶圓": [
                    {"symbol": "3105.TW", "name": "穩懋半導體", "name_en": "WIN Semiconductors (GaN Epi)"},
                    {"symbol": "2448.TW", "name": "晶元光電",   "name_en": "Epistar (GaN/LED Epi)"},
                    {"symbol": "6104.TW", "name": "創杰科技",   "name_en": "Carsem Semiconductor"},
                ],
            },
        },
        "資源": {
            "稀土": [],
            "黃金": [
                {"symbol": "00635U.TW", "name": "元大黃金", "name_en": "Yuanta Gold ETF"},
            ],
            "銅礦": [],
            "鐵礦鋼鐵": [
                {"symbol": "2002.TW", "name": "中鋼",       "name_en": "China Steel Corporation"},
                {"symbol": "2015.TW", "name": "豐興鋼鐵",   "name_en": "Feng Hsin Steel"},
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
