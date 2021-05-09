import datetime
import json
import numpy as np
import requests
import pandas as pd
import streamlit as st
from copy import deepcopy
import random

# faking chrome browser
browser_header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}
user_agent_list = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    ]
user_agent = random.choice(user_agent_list)
headers = {'User-Agent': user_agent}
st.set_page_config(layout='wide', initial_sidebar_state='collapsed')

@st.cache(allow_output_mutation=True, suppress_st_warning=True)
def load_mapping():
    df = pd.read_csv("district_mapping.csv")
    return df

def filter_column(df, col, value):
    df_temp = deepcopy(df.loc[df[col] == value, :])
    return df_temp

def filter_capacity(df, col, value):
    df_temp = deepcopy(df.loc[df[col] > value, :])
    return df_temp


mapping_df = load_mapping()

mapping_dict = pd.Series(mapping_df["district id"].values,
                         index = mapping_df["district name"].values).to_dict()

rename_mapping = {
    'date': 'Date',
    'min_age_limit': 'Minimum Age Limit',
    'available_capacity': 'Available Capacity',
    'vaccine': 'Vaccine',
    'pincode': 'Pincode',
    'name': 'Hospital Name',
    'state_name' : 'State',
    'district_name' : 'District',
    'block_name': 'Block Name',
    'fee_type' : 'Fees'
    }

st.title('CoWIN Vaccination Slot Availability')
st.info('The CoWIN APIs are geo-fenced so sometimes you may not see an output! Please try after sometime ')

# numdays = st.sidebar.slider('Select Date Range', 0, 100, 10)
unique_districts = list(mapping_df["district name"].unique())
unique_districts.sort()

left_column_1, right_column_1 = st.beta_columns(2)
with left_column_1:
    numdays = st.slider('Select Date Range', 0, 100, 5)

with right_column_1:
    dist_inp = st.selectbox('Select District', unique_districts)

DIST_ID = mapping_dict[dist_inp]

base = datetime.datetime.today()
date_list = [base + datetime.timedelta(days=x) for x in range(numdays)]
date_str = [x.strftime("%d-%m-%Y") for x in date_list]

final_df = None
for INP_DATE in date_str:
    URL = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={}&date={}".format(DIST_ID, INP_DATE)
    response = requests.get(URL, headers=headers)
    if (response.ok) and ('centers' in json.loads(response.text)):
        resp_json = json.loads(response.text)['centers']
        if resp_json is not None:
            df = pd.DataFrame(resp_json)
            if len(df):
                df = df.explode("sessions")
                df['min_age_limit'] = df.sessions.apply(lambda x: x['min_age_limit'])
                df['vaccine'] = df.sessions.apply(lambda x: x['vaccine'])
                df['available_capacity'] = df.sessions.apply(lambda x: x['available_capacity'])
                df['date'] = df.sessions.apply(lambda x: x['date'])
                df = df[["date", "available_capacity", "vaccine", "min_age_limit", "pincode", "name", "state_name", "district_name", "block_name", "fee_type"]]
                if final_df is not None:
                    final_df = pd.concat([final_df, df])
                else:
                    final_df = deepcopy(df)
            else:
                st.error("No rows in the data Extracted from the API")
#     else:
#         st.error("Invalid response")

if (final_df is not None) and (len(final_df)):
    final_df.drop_duplicates(inplace=True)
    final_df.rename(columns=rename_mapping, inplace=True)

    left_column_2, center_column_2, right_column_2, right_column_2a = st.beta_columns(4)
    with left_column_2:
        valid_pincodes = list(np.unique(final_df["Pincode"].values))
        pincode_inp = st.selectbox('Select Pincode', [""] + valid_pincodes)
        if pincode_inp != "":
            final_df = filter_column(final_df, "Pincode", pincode_inp)

    with center_column_2:
        valid_age = [18, 45]
        age_inp = st.selectbox('Select Minimum Age', [""] + valid_age)
        if age_inp != "":
            final_df = filter_column(final_df, "Minimum Age Limit", age_inp)

    with right_column_2:
        valid_payments = ["Free", "Paid"]
        pay_inp = st.selectbox('Select Free or Paid', [""] + valid_payments)
        if pay_inp != "":
            final_df = filter_column(final_df, "Fees", pay_inp)

    with right_column_2a:
        valid_capacity = ["available"]
        cap_inp = st.selectbox('Select Availablilty', [""] + valid_capacity)
        if cap_inp != "":
            final_df = filter_capacity(final_df, "Available Capacity", 0)

    table = deepcopy(final_df)
    table.reset_index(inplace=True, drop=True)
    st.table(table)
else:
    st.error("Unable to fetch data currently, please try after sometime")

st.markdown("_- Sahil Tanwar_")
