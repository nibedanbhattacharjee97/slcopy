import streamlit as st
import pandas as pd
import mysql.connector
import calendar
from datetime import datetime
import base64
from io import BytesIO

st.image("dddd.jpg", use_container_width=True)

# Function to establish MySQL connection
def get_mysql_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="anudip"
    )

# Function to load data from Excel into a DataFrame with caching
@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None})
def load_data(file):
    df = pd.read_excel(file)
    df.rename(columns={'Actual_Manager_Column_Name': 'Manager Name', 'Actual_SPOC_Column_Name': 'SPOC Name'}, inplace=True)
    return df

# Function to insert booking
def insert_booking(date, time_range, manager, spoc, booked_by):
    if not booked_by:
        st.error('Slot booking failed. Please provide your name in the "Slot Booked By" field.')
        return

    selected_date = datetime.strptime(date, '%Y-%m-%d')
    current_date = datetime.now()
    holidays = ['2024-10-31', '2024-11-09', '2024-11-16']

    if selected_date.strftime('%Y-%m-%d') in holidays:
        st.error('Booking Closed')
        return

    if selected_date < current_date:
        st.error('Cannot book slots for past dates.')
        return

    if selected_date.weekday() == 6:
        st.error('Booking unavailable on Sundays. Contact the admin.')
        return

    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointment_bookings WHERE date = %s AND spoc = %s", (date, spoc))
    existing_booking = cursor.fetchone()

    if existing_booking:
        conn.close()
        st.error('This SPOC is already booked for the selected date.')
        return

    cursor.execute("INSERT INTO appointment_bookings (date, time_range, manager, spoc, booked_by) VALUES (%s, %s, %s, %s, %s)",
                   (date, time_range, manager, spoc, booked_by))
    conn.commit()
    conn.close()
    st.success('Slot booked successfully!')

# Function to update another MySQL table
def update_another_database(file):
    df = pd.read_excel(file)
    conn = get_mysql_connection()
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("INSERT INTO plana (cmis_id, student_name, cmis_ph_no, center_name, uploader_name, verification_type, mode_of_verification, verification_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                       (row['CMIS ID'], row['Student Name'], row['CMIS PH No(10 Number)'],
                        row['Center Name'], row['Name Of Uploder'], row['Verification Type'], row['Mode Of Verification'], row['Verification Date']))
    conn.commit()
    conn.close()
    st.success('Data updated successfully!')

# Function to download data from MySQL
def download_another_database_data():
    conn = get_mysql_connection()
    df = pd.read_sql("SELECT * FROM plana", conn)
    conn.close()
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="plana.csv">Download CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

# Main function for Streamlit app
def main():
    st.title('Slot Booking Platform')
    data = load_data('managers_spocs.xlsx')
    selected_manager = st.selectbox('Select Manager', data['Manager Name'].unique())
    spocs_for_manager = data[data['Manager Name'] == selected_manager]['SPOC Name'].tolist()
    selected_spoc = st.selectbox('Select SPOC', spocs_for_manager)
    selected_date = st.date_input('Select Date')
    time_ranges = ['10:00 AM - 11:00 AM', '11:00 AM - 12:00 PM', '12:00 PM - 1:00 PM', '2:00 PM - 3:00 PM', '3:00 PM - 4:00 PM']
    selected_time_range = st.selectbox('Select Time', time_ranges)
    booked_by = st.text_input('Slot Booked By')
    file = st.file_uploader('Upload Excel', type=['xlsx', 'xls'])
    
    if file is not None and st.button('Update Data'):
        update_another_database(file)
    
    if st.button('Book Slot'):
        insert_booking(str(selected_date), selected_time_range, selected_manager, selected_spoc, booked_by)
    
    if st.button('Download Data For M&E Purpose'):
        download_another_database_data()
    
    conn = get_mysql_connection()
    df = pd.read_sql("SELECT * FROM appointment_bookings", conn)
    conn.close()
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    st.subheader("Today's Bookings")
    current_date = datetime.now().strftime("%Y-%m-%d")
    today_bookings = df[df['date'] == current_date]
    if not today_bookings.empty:
        for _, row in today_bookings.iterrows():
            st.write(f"- Time Slot: {row['time_range']}, Manager: {row['manager']}, SPOC: {row['spoc']}")
    else:
        st.write("No bookings for today.")

if __name__ == '__main__':
    main()
