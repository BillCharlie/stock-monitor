#!/usr/bin/env python3
"""
Test script for new Stock Monitor features.
Tests: symbol validation, realtime data, chip analysis, and institution identification.
"""
import sys
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8765"

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def test_symbol_validation():
    """Test symbol validation for custom stocks."""
    print(f"\n{BLUE}━━━ 测试 1: 符号验证 ━━━{RESET}")
    
    from realtime_data import validate_symbol
    
    # Test Taiwan stock
    print(f"{YELLOW}测试台湾股票: 2330.TW{RESET}")
    result = validate_symbol("2330.TW")
    if result.get("valid"):
        print(f"{GREEN}✓ 有效{RESET} - 价格: {result.get('price')}")
    else:
        print(f"{RED}✗ 无效{RESET} - {result.get('error')}")
    
    # Test US stock
    print(f"{YELLOW}测试美国股票: AAPL{RESET}")
    result = validate_symbol("AAPL")
    if result.get("valid"):
        print(f"{GREEN}✓ 有效{RESET} - 价格: {result.get('price')}")
    else:
        print(f"{RED}✗ 无效{RESET} - {result.get('error')}")
    
    # Test invalid symbol
    print(f"{YELLOW}测试无效符号: INVALID123{RESET}")
    result = validate_symbol("INVALID123")
    if not result.get("valid"):
        print(f"{GREEN}✓ 正确识别为无效{RESET} - {result.get('error')}")
    else:
        print(f"{RED}✗ 意外有效{RESET}")


def test_realtime_quote():
    """Test real-time quote API."""
    print(f"\n{BLUE}━━━ 测试 2: 实时报价 ━━━{RESET}")
    
    from realtime_data import get_realtime_quote
    
    symbols = ["2330.TW", "AAPL", "MSFT"]
    
    for symbol in symbols:
        print(f"{YELLOW}获取 {symbol} 的实时报价...{RESET}")
        try:
            quote = get_realtime_quote(symbol)
            if "error" not in quote:
                print(f"{GREEN}✓ 成功{RESET}")
                print(f"  价格: {quote.get('price')}")
                print(f"  买入: {quote.get('bid')}")
                print(f"  卖出: {quote.get('ask')}")
                print(f"  源: {quote.get('source')}")
            else:
                print(f"{RED}✗ 失败{RESET} - {quote.get('error')}")
        except Exception as e:
            print(f"{RED}✗ 异常{RESET} - {e}")


def test_intraday_kline():
    """Test intraday K-line API."""
    print(f"\n{BLUE}━━━ 测试 3: 盘中K线 ━━━{RESET}")
    
    from realtime_data import get_intraday_kline
    
    print(f"{YELLOW}获取 2330.TW 的1分钟K线...{RESET}")
    try:
        klines = get_intraday_kline("2330.TW", interval=1)
        if klines:
            print(f"{GREEN}✓ 成功获取 {len(klines)} 根K线{RESET}")
            # Show last 3 bars
            for i, bar in enumerate(klines[-3:], 1):
                print(f"  [{i}] {bar.get('time')} - Open:{bar.get('open'):.2f} "
                      f"High:{bar.get('high'):.2f} Low:{bar.get('low'):.2f} "
                      f"Close:{bar.get('close'):.2f} Vol:{bar.get('volume'):,}")
        else:
            print(f"{RED}✗ 无数据{RESET}")
    except Exception as e:
        print(f"{RED}✗ 异常{RESET} - {e}")


def test_chip_analysis():
    """Test chip/shareholder analysis."""
    print(f"\n{BLUE}━━━ 测试 4: 筹码分析 ━━━{RESET}")
    
    from chip_analysis import get_twse_chip_distribution
    
    print(f"{YELLOW}获取 2330.TW 的筹码分析...{RESET}")
    try:
        chip = get_twse_chip_distribution("2330.TW")
        if "error" not in chip:
            print(f"{GREEN}✓ 成功{RESET}")
            
            # Concentration info
            conc = chip.get("concentration", {})
            print(f"  集中度: {conc.get('level')} (HHI={conc.get('hhi')})")
            print(f"  前10大股东占比: {conc.get('top_10_pct')}%")
            
            # Institutional info
            inst = chip.get("institutional_ownership", {})
            print(f"  机构所有权: {inst.get('institutional_pct')}%")
            print(f"  零售所有权: {inst.get('retail_pct')}%")
            print(f"  主导: {inst.get('institutional_dominance')}")
            
            # Top holders
            holders = chip.get("major_holders", [])[:3]
            print(f"  前3大股东:")
            for h in holders:
                print(f"    - {h.get('name')} ({h.get('type')}): {h.get('percentage')}%")
        else:
            print(f"{RED}✗ 失败{RESET} - {chip.get('error')}")
    except Exception as e:
        print(f"{RED}✗ 异常{RESET} - {e}")


def test_major_traders():
    """Test major trader analysis."""
    print(f"\n{BLUE}━━━ 测试 5: 主力交易分析 ━━━{RESET}")
    
    from chip_analysis import get_major_trader_analysis
    
    print(f"{YELLOW}获取 2330.TW 的主力交易分析...{RESET}")
    try:
        traders = get_major_trader_analysis("2330.TW")
        if "error" not in traders:
            print(f"{GREEN}✓ 成功{RESET}")
            
            vol = traders.get("volume_analysis", {})
            print(f"  平均日成交量: {vol.get('avg_daily_volume'):,} 股")
            print(f"  高成交量日数: {vol.get('high_volume_days')}")
            print(f"  成交量趋势: {vol.get('volume_trend')}")
            
            recent = traders.get("recent_high_volume", [])
            if recent:
                print(f"  最近高成交量日期:")
                for day in recent[:3]:
                    print(f"    - {day.get('date')}: {day.get('volume'):,} ({day.get('volume_rate')}x)")
        else:
            print(f"{RED}✗ 失败{RESET} - {traders.get('error')}")
    except Exception as e:
        print(f"{RED}✗ 异常{RESET} - {e}")


def test_institution_identification():
    """Test institution identification."""
    print(f"\n{BLUE}━━━ 测试 6: 机构识别 ━━━{RESET}")
    
    from stock_data import get_investors_data
    from chip_analysis import identify_major_institutions
    
    print(f"{YELLOW}识别 2330.TW 的主力机构...{RESET}")
    try:
        investors_data = get_investors_data("2330.TW")
        if "error" not in investors_data:
            institutions = identify_major_institutions("2330.TW", investors_data)
            
            print(f"{GREEN}✓ 成功{RESET}")
            
            # Show latest three forces data
            print(f"  最新三大法人数据:")
            print(f"    - 日期: {investors_data.get('latest_date')}")
            print(f"    - 外资: {investors_data.get('foreign_net'):,} 股")
            print(f"    - 投信: {investors_data.get('trust_net'):,} 股")
            print(f"    - 自营: {investors_data.get('dealer_net'):,} 股")
            print(f"    - 合计: {investors_data.get('total_net'):,} 股")
            
            # Show likely buyers
            buyers = institutions.get("likely_buyers", [])
            if buyers:
                print(f"  可能的买方:")
                for buyer in buyers[:2]:
                    print(f"    - {buyer.get('type')}: {buyer.get('signal')}")
                    for inst in buyer.get('likely_institutions', [])[:2]:
                        print(f"      → {inst}")
            
            # Show likely sellers
            sellers = institutions.get("likely_sellers", [])
            if sellers:
                print(f"  可能的卖方:")
                for seller in sellers[:2]:
                    print(f"    - {seller.get('type')}: {seller.get('signal')}")
            
            # Show sentiment
            summary = institutions.get("trend_summary", {})
            print(f"  市场情绪: {summary.get('sentiment')}")
        else:
            print(f"{RED}✗ 失败{RESET} - {investors_data.get('error')}")
    except Exception as e:
        print(f"{RED}✗ 异常{RESET} - {e}")


def print_summary():
    """Print test summary."""
    print(f"\n{BLUE}{'='*50}{RESET}")
    print(f"{BLUE}测试完成{RESET}")
    print(f"{BLUE}{'='*50}{RESET}")
    print(f"\n{YELLOW}提示:{RESET}")
    print(f"- 所有测试都使用本地数据源（不依赖API密钥）")
    print(f"- 实时数据来自 TWSE、腾讯财经、新浪财经")
    print(f"- 筹码和机构数据来自 TWSE 公开数据")
    print(f"- 更多功能请参考 ENHANCEMENTS.md")


if __name__ == "__main__":
    print(f"\n{BLUE}{'='*50}{RESET}")
    print(f"{BLUE}Stock Monitor 新功能测试{RESET}")
    print(f"{BLUE}{'='*50}{RESET}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        test_symbol_validation()
        test_realtime_quote()
        test_intraday_kline()
        test_chip_analysis()
        test_major_traders()
        test_institution_identification()
        print_summary()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}测试被中断{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}严重错误: {e}{RESET}")
        sys.exit(1)
