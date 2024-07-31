import pandas as pd
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid

# Initializing Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("C:\\Users\\huzaifa\\Desktop\\sales-tracker.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Fruits dictionary {key: value}
fruits = {
    'apple': 100,
    'banana': 40,
    'orange': 70,
    'grapes': 120,
    'mango': 180
}

# Vegetables dictionary {key: value}
vegetables = {
    'carrot': 30,
    'broccoli': 60,
    'spinach': 25,
    'potato': 40,
    'tomato': 40
}

# Dairy dictionary {key: value}
dairy = {
    'milk': 24,
    'curd': 28,
    'butter': 170,
    'cheese': 18
}

# CGST and SGST rates
CGST_RATE = 0.09
SGST_RATE = 0.09

# Initializing session state 
if 'transactions_df' not in st.session_state:
    st.session_state.transactions_df = pd.DataFrame(columns=['Product Name', 'Quantity', 'Amount', 'Date', 'Price'])

# Function for generating unique code
def generate_unique_code():
    return str(uuid.uuid4())

def enter_product(product_name, quantity, current_date):
    if product_name in fruits or product_name in vegetables or product_name in dairy:
        price_per_unit = fruits.get(product_name, vegetables.get(product_name, dairy.get(product_name)))
        amount = price_per_unit * quantity

        current_date_str = current_date.strftime('%Y-%m-%d')

        new_transaction = pd.DataFrame([[product_name, quantity, amount, current_date_str, price_per_unit]],
                                       columns=['Product Name', 'Quantity', 'Amount', 'Date', 'Price'])
        st.session_state.transactions_df = pd.concat([st.session_state.transactions_df, new_transaction], ignore_index=True)

# Function to generate bill
def generate_bill(current_date):
    transactions_df = st.session_state.transactions_df
    if not transactions_df.empty:
        filtered_transactions = transactions_df[transactions_df['Date'] == current_date.strftime('%Y-%m-%d')]
        if not filtered_transactions.empty:
            st.write("Bill:")
            filtered_transactions['CGST'] = filtered_transactions['Amount'] * CGST_RATE
            filtered_transactions['SGST'] = filtered_transactions['Amount'] * SGST_RATE
            filtered_transactions['Total Amount'] = filtered_transactions['Amount'] + filtered_transactions['CGST'] + filtered_transactions['SGST']
            st.write(filtered_transactions[['Product Name', 'Quantity', 'Price', 'Amount', 'CGST', 'SGST', 'Total Amount']])

            total_amount = filtered_transactions['Amount'].sum()
            total_cgst = filtered_transactions['CGST'].sum()
            total_sgst = filtered_transactions['SGST'].sum()
            grand_total = total_amount + total_cgst + total_sgst

            st.write(f"Total Amount: ₹{total_amount:.2f}")
            st.write(f"Total CGST (9%): ₹{total_cgst:.2f}")
            st.write(f"Total SGST (9%): ₹{total_sgst:.2f}")
            st.write(f"Grand Total: ₹{grand_total:.2f}")

            bill_id = generate_unique_code()
            bill_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'total_amount': total_amount,
                'total_cgst': total_cgst,
                'total_sgst': total_sgst,
                'grand_total': grand_total,
                'transactions': filtered_transactions.to_dict('records')
            }
            db.collection('bills').document(bill_id).set(bill_data)

        else:
            st.write("No transactions for the selected date.")
    else:
        st.write("No transactions to display.")

# Function for visualizations
def show_visualizations():
    bills_ref = db.collection('bills')
    bills_docs = bills_ref.stream()
    sales_data = []
    for doc in bills_docs:
        bill = doc.to_dict()
        for transaction in bill['transactions']:
            sales_data.append(transaction)
    
    sales_data = pd.DataFrame(sales_data)
    if not sales_data.empty:
        st.subheader("Sales Overview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            total_sales = sales_data['Quantity'].sum()
            st.metric(label="Total Sales", value=total_sales)
        with col2:
            total_revenue = sales_data['Amount'].sum()
            st.metric(label="Total Revenue", value=f"₹{total_revenue:.2f}")
        with col3:
            total_products = sales_data['Product Name'].nunique()
            st.metric(label="Total Products Sold", value=total_products)

        st.subheader("Sales Count by Product")
        sales_count_chart = sales_data.groupby('Product Name')['Quantity'].sum()
        st.bar_chart(sales_count_chart)

        st.subheader("Sales Amount by Product")
        sales_amount_chart = sales_data.groupby('Product Name')['Amount'].sum()
        st.bar_chart(sales_amount_chart)

        st.subheader("Sales over Time")
        sales_time_chart = sales_data.groupby('Date')['Amount'].sum()
        st.line_chart(sales_time_chart)

        st.subheader("Product-Specific Report")
        products = sales_data['Product Name'].unique()
        selected_product = st.selectbox("Select a Product", products)
        
        product_data = sales_data[sales_data['Product Name'] == selected_product]
        if not product_data.empty:
            st.write(f"Report for {selected_product}:")
            
            total_sales = product_data['Quantity'].sum()
            total_amount = product_data['Amount'].sum()
            st.write(f"Total Sales Count: {total_sales}")
            st.write(f"Total Sales Amount: ₹{total_amount:.2f}")

            st.subheader("Sales Count Over Time")
            product_sales_time_chart = product_data.groupby('Date')['Quantity'].sum()
            st.line_chart(product_sales_time_chart)

            st.subheader("Sales Amount Over Time")
            product_amount_time_chart = product_data.groupby('Date')['Amount'].sum()
            st.line_chart(product_amount_time_chart)
        else:
            st.write(f"No data available for {selected_product}.")
    else:
        st.write("No sales data to visualize.")

page = st.selectbox("Select Page", ["Data Entry", "Visualizations"])
if page == "Data Entry":
    st.title("Sales Data Entry")
    st.header("Select From A Variety Of Products Below")

    current_date = st.date_input("Select the date", pd.to_datetime('today'))

    fruits_quantity = {}
    vegetables_quantity = {}
    dairy_quantity = {}

    with st.form("entry_form", clear_on_submit=True):
        with st.expander("FRUIT"):
            for fruit, price in fruits.items():
                fruits_quantity[fruit] = st.number_input(f"Quantity of {fruit}", min_value=0, value=0)
        
        with st.expander("VEGETABLES"):
            for veg, price in vegetables.items():
                vegetables_quantity[veg] = st.number_input(f"Quantity of {veg}", min_value=0, value=0)
        
        with st.expander("DAIRY"):
            for item, price in dairy.items():
                dairy_quantity[item] = st.number_input(f"Quantity of {item}", min_value=0, value=0)
        
        submitted = st.form_submit_button("Submit")

    if submitted:
        for product, quantity in {**fruits_quantity, **vegetables_quantity, **dairy_quantity}.items():
            if quantity > 0:
                enter_product(product, quantity, current_date)
        generate_bill(current_date)
        st.success("Data submitted and bill generated successfully.")

elif page == "Visualizations":
    show_visualizations()

