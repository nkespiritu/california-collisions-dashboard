import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime
import sqlite3
from sqlite3 import Connection
from pathlib import Path

dbPath = '../../../iCloud/Employment/Plentina/switrs.sqlite'

def main():
    st.title("California Collisions Monitor")
    conn = get_connection(dbPath)
    startDate, endDate, bikeBool, truckBool, pedBool, motorBool = build_sidebar()
    build_dashboard(conn, start_date=startDate, end_date=endDate, inolvedPartyBike=bikeBool,
                    involvedPartyTruck=truckBool, involvedPartyPedestrian=pedBool, involvedPartyMotorcycle=motorBool)
    fatality_rate(conn)

@st.cache(hash_funcs={Connection: id})
def get_connection(path: str):
    """Put the connection in cache to reuse if path does not change between Streamlit reruns.
    NB : https://stackoverflow.com/questions/48218065/programmingerror-sqlite-objects-created-in-a-thread-can-only-be-used-in-that-sa
    """
    return sqlite3.connect(path, check_same_thread=False)


@st.cache(hash_funcs={Connection: id}, suppress_st_warning=True)
def get_data(conn: Connection):
    query = '''
    SELECT case_id, latitude, longitude, collision_date, 
       collision_time, weather_1, weather_2, collision_severity,
       severe_injury_count, other_visible_injury_count, 
       complaint_of_pain_injury_count, pedestrian_killed_count,
       pedestrian_injured_count, bicyclist_killed_count,
       bicyclist_injured_count, motorcyclist_killed_count,
       motorcyclist_injured_count, killed_victims, injured_victims,
       party_count, primary_collision_factor, pcf_violation_code,
       pcf_violation_category, pcf_violation, pcf_violation_subsection,
       lighting, road_surface, road_condition_1, road_condition_2, 
       pedestrian_collision, bicycle_collision, motorcycle_collision, truck_collision,
       alcohol_involved, hit_and_run
    FROM collisions
    WHERE collision_date IS NOT NULL
    AND collision_time IS NOT NULL
    AND date(collision_date) BETWEEN date('2021-01-01') and date('2021-12-31')
    '''
    df = pd.read_sql_query(query, conn,
                        parse_dates=['collision_date'])
    return df

def build_sidebar():
    with st.sidebar.expander("Filter data"):
        startDateCol, endDateCol = st.columns(2)

        sd = startDateCol.date_input(label="Start Date",
                                            min_value=datetime(2021, 1, 1),
                                            max_value=datetime(2021, 6, 4),
                                            value=datetime(2021, 1, 1),
                                            key="sd1")
        ed = endDateCol.date_input(label="End Date",
                                        min_value=datetime(2021, 1, 1),
                                        max_value=datetime(2021, 6, 4),
                                        value=datetime(2021, 6, 4),
                                        key="ed1")

        st.write("**Involved Parties**")
        inolvedPartyBike = st.checkbox(label="Bicycle", value=False)
        involvedPartyTruck = st.checkbox(label="Truck", value=False)
        involvedPartyPedestrian = st.checkbox(label="Pedestrian", value=False)
        involvedPartyMotorcycle = st.checkbox(label="Motorcycle", value=False)
        st.write("**Page Navigation**")

        my_page = st.radio('Page Navigation', ['Daily Monitoring',
                                               'Weekly Monitoring',
                                               'Monthly Monitoring'])
    return sd, ed, inolvedPartyBike, involvedPartyTruck, involvedPartyPedestrian, involvedPartyMotorcycle


@st.cache(hash_funcs={Connection: id})
def fatality_rate(conn: Connection):
    # Based on:
    # https: // www.kaggle.com/alexgude/switrs-increase-in-traffic-fatalities-after-covid
    fatalityQuery = f"""
        SELECT collision_date
            , 1 as crashes
            , IIF(COLLISION_SEVERITY='fatal', 1, 0) as fatalitiesCount
        FROM collisions 
        WHERE collision_date IS NOT NULL 
        AND date(collision_date) BETWEEN date('2019-01-01') AND date('2021-12-31')
        """
    fatalityRateDF = pd.read_sql_query(fatalityQuery, conn, parse_dates=[
        "collision_date"]).groupby('collision_date').agg('sum')

    return fatalityRateDF


def build_dashboard(conn: Connection, start_date, end_date, inolvedPartyBike, involvedPartyTruck, involvedPartyPedestrian, involvedPartyMotorcycle):
    fatalityRate, countInjured = st.columns(2)

    df = get_data(conn)
    dateMask = (df['collision_date'].dt.date >= start_date) & (
        df['collision_date'].dt.date <= end_date)

    partyMask = (df['pedestrian_collision'] == involvedPartyPedestrian) | \
        (df['truck_collision'] == involvedPartyTruck) | \
        (df['bicycle_collision'] == inolvedPartyBike) | \
        (df['motorcycle_collision'] == involvedPartyMotorcycle)

    involvedDF = df.loc[dateMask].loc[partyMask]


    ##################
    # Average Weekly #
    # Fatality Rate  #
    ##################

    fatalityDF = fatality_rate(conn)
    fatalityDateMask = (fatalityDF.index.date >= start_date) & (
        fatalityDF.index.date <= end_date)
    with fatalityRate:


        weeklyFatalityRateDF = fatalityDF.loc[fatalityDateMask].resample(
            'W-MON').sum()
        weeklyFatalityRateDF['fatalitiesRate'] = weeklyFatalityRateDF['fatalitiesCount'] / \
            weeklyFatalityRateDF['crashes']
        meanWeeklyFatalityRate = np.mean(
            weeklyFatalityRateDF['fatalitiesRate'])*100
        strMWFRate = "{:.2f}%".format(meanWeeklyFatalityRate)
        st.subheader(strMWFRate)
        st.markdown("**Average Weekly Fatality Rate**")



    with countInjured:
        number = 111
        st.subheader(number)
        st.markdown("**Injured Victims**")






    mapDF = involvedDF[['collision_date', 'latitude', 'longitude']].dropna()
    st.map(mapDF[['latitude', 'longitude']].drop_duplicates())




if __name__ == "__main__":
    main()




# # ## Other graphs
# # hourlyGraphCol, collisionTypeGraphCol = st.columns(2)
# # st.write("Number of collisions per hour")
# # hourlyGraphCol.write()

# # if __name__ == "__main__":
# #     main()

# # if my_page == 'page 1':
# #     st.title('here is a page')
# #     button = st.button('a button')
# #     if button:
# #         st.write('clicked')
# # else:
# #     st.title('this is a different page')
# #     slide = st.slider('this is a slider')
# #     slide

# ## quick numbers

# 



# # if st.checkbox('Show dataframe'):
# #     chart_data = pd.DataFrame(
# #         np.random.randn(20, 3),
# #         columns=['a', 'b', 'c'])

# #     chart_data

# # option = st.selectbox(
# #     'Which number do you like best?',
# #     df['first column'])

# # 'You selected: ', option

# left_column, right_column = st.columns(2)
# pressed = left_column.button('Press me?')
# if pressed:
#   right_column.write("Woohoo!")

# expander = st.expander("FAQ")
# expander.write(
#     "Here you could put in some really, really long explanations...")




# # if __name__ == '__main__':

# #     df = pd.read_csv('file_path')

# #     st.title('Datetime Filter')
# #     filtered_df = df_filter('Move sliders to filter dataframe',df)

# #     column_1, column_2 = st.beta_columns(2)

# #     with column_1:
# #         st.title('Data Frame')
# #         st.write(filtered_df)

# #     with column_2:
# #         st.title('Chart')
# #         st.line_chart(filtered_df['value'])

# #     st.markdown(download_csv('Filtered Data Frame',filtered_df),unsafe_allow_html=True)












