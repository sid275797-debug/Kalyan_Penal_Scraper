import json
import os

# --------------------------------------------------------
# FIXED PATHS
# --------------------------------------------------------

PROFIT_REPORT_FILE = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\bet_profit_v11\profit_report.json"
PREMIUM_OUTPUT_FILE = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\bet_profit_v11\premium_profit_report.json"

# FINAL PREMIUM KEYWORDS
PREMIUM_KEYWORDS = ["KALYAN", "RAJDHANI", "MILAN", "TIME", "BAZAR", "SRIDEVI", "MAIN"]


# --------------------------------------------------------
# CHECK IF MARKET IS PREMIUM
# --------------------------------------------------------
def is_premium_market(market_name: str):
    m = market_name.upper()
    return any(keyword in m for keyword in PREMIUM_KEYWORDS)


# --------------------------------------------------------
# MAIN LOGIC
# --------------------------------------------------------
def main():
    if not os.path.isfile(PROFIT_REPORT_FILE):
        print("ERROR: profit_report.json not found.")
        print(f"Expected at: {PROFIT_REPORT_FILE}")
        return

    # Load complete profit report
    with open(PROFIT_REPORT_FILE, "r") as f:
        data = json.load(f)

    premium_only = {}
    total_net_profit = 0

    # Filter markets
    for market, details in data.items():
        if is_premium_market(market):
            premium_only[market] = details

            # Summing net profit
            np = details.get("net_profit", 0)
            if isinstance(np, (int, float)):
                total_net_profit += np

    # Add TOTAL ENTRY at the end
    premium_only["TOTAL_PREMIUM_NET_PROFIT"] = total_net_profit

    # Save filtered premium file
    with open(PREMIUM_OUTPUT_FILE, "w") as f:
        json.dump(premium_only, f, indent=4)

    print("\n✅ premium_profit_report.json generated successfully!")
    print(f"📁 Saved at: {PREMIUM_OUTPUT_FILE}")
    print(f"⭐ Total premium markets: {len(premium_only) - 1}")
    print(f"💰 TOTAL PREMIUM NET PROFIT: {total_net_profit}")


if __name__ == "__main__":
    main()
