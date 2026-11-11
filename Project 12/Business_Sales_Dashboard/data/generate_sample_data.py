"""Creates data/sample_sales.csv  (100% synthetic data, currency = PKR).

Run from the project root:   python data/generate_sample_data.py
A few deliberately 'dirty' rows are added at the end so the cleaning
step of the dashboard has something real to report.
"""
import random
import pandas as pd

random.seed(42)

# product: (category, selling price, cost)
PRODUCTS = {
    "Laptop": ("Electronics", 95000, 78000),
    "Smartphone": ("Electronics", 60000, 48000),
    "Wireless Earbuds": ("Electronics", 9000, 5500),
    "Smart Watch": ("Electronics", 15000, 10000),
    "Office Chair": ("Furniture", 22000, 14000),
    "Study Desk": ("Furniture", 28000, 18500),
    "Bookshelf": ("Furniture", 16000, 10500),
    "Notebook Pack": ("Stationery", 800, 450),
    "Gel Pen Box": ("Stationery", 600, 330),
    "Printer Paper Ream": ("Stationery", 1500, 1100),
    "Water Bottle": ("Home & Kitchen", 1800, 900),
    "Air Fryer": ("Home & Kitchen", 18000, 12500),
    "Blender": ("Home & Kitchen", 8500, 5600),
    "Backpack": ("Accessories", 5500, 3000),
    "Phone Case": ("Accessories", 1200, 400),
}
NAMES = ["Ali Khan", "Sara Ahmed", "Usman Tariq", "Ayesha Malik", "Bilal Hussain",
         "Hina Raza", "Hamza Sheikh", "Fatima Noor", "Zain Abbas", "Maryam Iqbal",
         "Hassan Raza", "Noor Fatima", "Asad Mehmood", "Sana Javed", "Talha Butt",
         "Iqra Siddiqui", "Faisal Qureshi", "Mehwish Ali", "Danish Aslam", "Rabia Khan",
         "Imran Ghani", "Laiba Shah", "Kamran Akbar", "Zara Yousaf", "Owais Hanif",
         "Amna Rauf", "Shahid Mirza", "Bushra Anwar", "Adeel Farooq", "Komal Rehman",
         "Junaid Aziz", "Hira Nadeem", "Salman Baig", "Eman Zahid", "Rizwan Chaudhry",
         "Nimra Saeed", "Waqar Younas", "Alina Pervez", "Yasir Latif", "Tooba Kamal"]
REGIONS = ["Islamabad", "Rawalpindi", "Lahore", "Karachi", "Peshawar"]

customers = []
for i, name in enumerate(NAMES):
    customers.append((f"CUST-{101 + i}", name, random.choice(REGIONS)))
weights = [random.choice([1, 1, 2, 3, 6]) for _ in customers]  # some customers buy far more often

start, end = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-06-30")
days = pd.date_range(start, end)
day_weights = [1 + 0.25 * d.month for d in days]  # sales slowly grow over time

rows = []
for n in range(360):
    order_id = f"ORD-{1001 + n}"
    if n == 0:
        date = start
    elif n == 1:
        date = end
    else:
        date = random.choices(days, weights=day_weights)[0]
    cust_id, cust_name, region = random.choices(customers, weights=weights)[0]
    for product in random.sample(list(PRODUCTS), random.choice([1, 1, 2, 3])):
        category, price, cost = PRODUCTS[product]
        qty = random.randint(1, 2) if price >= 15000 else random.randint(1, 8)
        unit_price = round(price * random.choice([1, 1, 1, 0.95, 0.9]) / 100) * 100
        rows.append([order_id, date.strftime("%Y-%m-%d"), cust_id, cust_name,
                     product, category, qty, unit_price, cost, region])

cols = ["Order_ID", "Order_Date", "Customer_ID", "Customer_Name", "Product",
        "Category", "Quantity", "Unit_Price", "Unit_Cost", "Region"]
df = pd.DataFrame(rows, columns=cols)

# ---- deliberately dirty rows (to demonstrate the cleaning report) ----
dirty = df.sample(4, random_state=1)                       # 4 exact duplicates
bad_qty = df.iloc[[5]].copy();  bad_qty["Order_ID"] = "ORD-9001"; bad_qty["Quantity"] = 0
bad_date = df.iloc[[9]].copy(); bad_date["Order_ID"] = "ORD-9002"; bad_date["Order_Date"] = "not a date"
no_name = df.iloc[[12]].copy(); no_name["Order_ID"] = "ORD-9003"; no_name["Customer_Name"] = None
df = pd.concat([df, dirty, bad_qty, bad_date, no_name], ignore_index=True)

df.to_csv("data/sample_sales.csv", index=False)
print(f"Saved data/sample_sales.csv with {len(df)} rows")
