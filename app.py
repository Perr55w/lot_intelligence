import os
import sqlite3
import anthropic

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "lot_intelligence.db")

SCHEMA = """
Tables in the lot_intelligence database:

dealers(dealer_id, dealer_name, dealer_type, state, years_active)
  - dealer_type: 'franchise' or 'independent'
  - state: 2-letter US state code

vehicles(vehicle_id, vin, make, model, year, trim, mileage, color, condition_grade, fuel_type, body_style)
  - condition_grade: 1.0-5.0 (higher is better)
  - fuel_type: 'Gasoline', 'Electric', 'Hybrid'
  - body_style: 'Sedan', 'SUV', 'Truck', 'Hatchback', 'Coupe', 'Van'

auctions(auction_id, vehicle_id, auction_date, location, lane_number, sale_type)
  - sale_type: e.g. 'sold', 'no_sale', 'if_sale'
  - auction_date: 'YYYY-MM-DD' format

transactions(transaction_id, auction_id, seller_id, buyer_id, sale_price, mmr_value, sale_status)
  - sale_price and mmr_value are in USD
  - sale_status: e.g. 'completed', 'arbitration'
  - seller_id and buyer_id reference dealers.dealer_id

market_index(index_id, month, segment, adjusted_index, non_adjusted_index, yoy_change)
  - segment: vehicle segment/category
  - yoy_change: year-over-year percent change

Key relationships:
  auctions.vehicle_id       -> vehicles.vehicle_id
  transactions.auction_id   -> auctions.auction_id
  transactions.seller_id    -> dealers.dealer_id
  transactions.buyer_id     -> dealers.dealer_id
"""

SYSTEM_PROMPT = f"""You are a SQL expert for a Manheim-style vehicle auction database.
Given a plain English question, return ONLY a single valid SQLite SELECT query.
No explanation. No markdown. No code blocks. Just the raw SQL.
If the question cannot be answered from the schema, respond with exactly: UNABLE_TO_ANSWER

{SCHEMA}"""


def ask(question: str) -> str:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    sql = message.content[0].text.strip()
    print(f"SQL: {sql}\n")

    if sql == "UNABLE_TO_ANSWER":
        return "That question can't be answered from the available data."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    conn.close()

    if not rows:
        return "No results found."

    result = "SQL: " + sql + "\n\n"
    result += " | ".join(columns) + "\n"
    result += "-" * 60 + "\n"
    for row in rows:
        result += " | ".join(str(v) for v in row) + "\n"
    result += f"\n{len(rows)} row(s)"
    return result


if __name__ == "__main__":
    print("Lot Intelligence - Natural Language SQL")
    print("Type 'quit' to exit\n")

    while True:
        question = input("Ask a question: ").strip()
        if not question:
            continue
        if question.lower() == "quit":
            break
        print()
        print(ask(question))
        print()
