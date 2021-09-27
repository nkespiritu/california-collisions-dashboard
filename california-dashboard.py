import time
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
import sqlite3
from sqlite3 import Connection
from pathlib import Path
from bokeh.plotting import figure


dbPath = '../../../iCloud/Employment/Plentina/switrs.sqlite'

countyCodes = {
    '01': 'Alameda',
    '02': 'Alpine',
    '03': 'Amador',
    '04': 'Butte',
    '05': 'Calaveras',
    '06': 'Colusa',
    '07': 'Contra Costa',
    '08': 'Del Norte',
    '09': 'El Dorado',
    '10': 'Fresno',
    '11': 'Glenn',
    '12': 'Humboldt',
    '13': 'Imperial',
    '14': 'Inyo',
    '15': 'Kern',
    '16': 'Kings',
    '17': 'Lake',
    '18': 'Lassen',
    '19': 'Los Angeles',
    '20': 'Madera',
    '21': 'Marin',
    '22': 'Mariposa',
    '23': 'Mendocino',
    '24': 'Merced',
    '25': 'Modoc',
    '26': 'Mono',
    '27': 'Monterey',
    '28': 'Napa',
    '29': 'Nevada',
    '30': 'Orange',
    '31': 'Placer',
    '32': 'Plumas',
    '33': 'Riverside',
    '34': 'Sacramento',
    '35': 'San Benito',
    '36': 'San Bernardino',
    '37': 'San Diego',
    '38': 'San Francisco',
    '39': 'San Joaquin',
    '40': 'San Luis Obispo',
    '41': 'San Mateo',
    '42': 'Santa Barbara',
    '43': 'Santa Clara',
    '44': 'Santa Cruz',
    '45': 'Shasta',
    '46': 'Sierra',
    '47': 'Siskiyou',
    '48': 'Solano',
    '49': 'Sonoma',
    '50': 'Stanislaus',
    '51': 'Sutter',
    '52': 'Tehama',
    '53': 'Trinity',
    '54': 'Tulare',
    '55': 'Tuolumne',
    '56': 'Ventura',
    '57': 'Yolo',
    '58': 'Yuba'
}

def main():
    st.title("California Vehicular Incidents Monitor")
    conn = get_connection(dbPath)
    startDate, endDate, county, alcoholBool = build_sidebar()
    
    countFatalities, countInjured = st.columns(2)
    countPedestrianF, countPedestrianI = st.columns(2)
    countCyclistF, countCyclistI = st.columns(2)
    
    fatalitiesPer1000, injuriesPer1000, pedF, pedI, cyF, cyI, mapDF, hourlyFig, topFactorsDF = build_dashboard(conn,
        start_date=startDate, end_date=endDate, 
        specificCountyFilter=county, alcoholFilter=alcoholBool)
    
    with countFatalities:
        st.subheader(fatalitiesPer1000)
        st.markdown("**Fatalities per 1,000 population**")

    with countInjured:
        st.subheader(injuriesPer1000)
        st.markdown("**Injured per 1,000 population**")
    
    with countPedestrianF:
        st.subheader(pedF)
        st.markdown("*Pedestrian fatalities*")

    with countPedestrianI:
        st.subheader(pedI)
        st.markdown("*Injured pedestrian*")
    
    with countCyclistF:
        st.subheader(cyF)
        st.markdown("*Bicyclist fatalities*")

    with countCyclistI:
        st.subheader(cyI)
        st.markdown("*Injured bicyclists*")

    st.markdown("### Locations of filtered collisions")
    st.map(mapDF)
    
    graphInjuries, graphFactors = st.columns(2)
    
    with graphInjuries:
        st.markdown("### Victims per hour")
        st.bokeh_chart(hourlyFig, use_container_width=True)
    
    with graphFactors:
        st.markdown("### Top 10 factors of collision")
        st.table(topFactorsDF)

@st.cache(hash_funcs={Connection: id})
def get_connection(path: str):
    """Put the connection in cache to reuse if path does not change between Streamlit reruns.
    NB : https://stackoverflow.com/questions/48218065/programmingerror-sqlite-objects-created-in-a-thread-can-only-be-used-in-that-sa
    """
    return sqlite3.connect(path, check_same_thread=False)


@st.cache(hash_funcs={Connection: id}, suppress_st_warning=True, allow_output_mutation=True)
def get_data(conn: Connection):
    query = '''
    SELECT case_id, latitude, longitude, collision_date, 
       SUBSTR(county_city_location, -4, 2) AS county_code,
       collision_time, severe_injury_count, pedestrian_killed_count,
       pedestrian_injured_count, bicyclist_killed_count,
       bicyclist_injured_count, killed_victims, injured_victims,
       pcf_violation_category, alcohol_involved
    FROM collisions
    WHERE collision_date IS NOT NULL
    AND collision_time IS NOT NULL
    AND chp_beat_type IS NOT 'interstate'
    AND date(collision_date) BETWEEN date('2019-06-04') and date('2021-12-31')
    '''

# include other columns in next iteration:
# pedestrian_collision, bicycle_collision, motorcycle_collision, 
# truck_collision, lighting, road_surface, road_condition_1, 
# road_condition_2, hit_and_run, pcf_violation, pcf_violation_subsection,
# pcf_violation_code, primary_collision_factor, party_count,
# motorcyclist_killed_count, motorcyclist_injured_count,
# weather_1, weather_2, collision_severity, other_visible_injury_count,
# complaint_of_pain_injury_count

    df = pd.read_sql_query(query, conn,
                        parse_dates=['collision_date'])
    return df

#@st.cache(hash_funcs={Connection: id})
def build_sidebar():
    st.sidebar.image('logo.png', use_column_width=True)
    st.sidebar.write("**Filter data**")
    ###############
    # Date Filter #
    ###############

    startDateCol, endDateCol = st.sidebar.columns(2)

    sd = startDateCol.date_input(label="Start Date",
                                        min_value=datetime(2019, 6, 4),
                                        max_value=datetime(2021, 6, 4),
                                        value=datetime(2019, 6, 4),
                                        key="sd1")
    ed = endDateCol.date_input(label="End Date",
                                    min_value=datetime(2019, 6, 4),
                                    max_value=datetime(2021, 6, 4),
                                    value=datetime(2021, 6, 4),
                                    key="ed1")

    #################
    # County Filter #
    #################

    countyKey = 0
    with st.sidebar.expander(label="Click here to choose county:"):
        allCounties = ['All Counties']
        countiesList = [county for county in countyCodes.values()]
        allCounties.extend(countiesList)
        specificCountyFilter = st.radio(label="Choose county:",
                                        options=allCounties,
                                        index=0,
                                        key=countyKey)
    countyKey += 1
    if specificCountyFilter:
        st.sidebar.write("You selected: ", specificCountyFilter)
    
    

    ###########################
    # Involved Parties Filter #
    ###########################

    # st.sidebar.write("**Involved Parties**")
    # inolvedPartyBike = st.sidebar.checkbox(
    #     label="Bicycle", value=False, help="Applies to map only")
    # involvedPartyTruck = st.sidebar.checkbox(
    #     label="Truck", value=False, help="Applies to map only")
    # involvedPartyPedestrian = st.sidebar.checkbox(
    #     label="Pedestrian", value=False, help="Applies to map only")
    # involvedPartyMotorcycle = st.sidebar.checkbox(
    #     label="Motorcycle", value=False, help="Applies to map only")

    alcoholFilter = st.sidebar.checkbox(label="Is alcohol involved?", value=False)

    return sd, ed, specificCountyFilter, alcoholFilter



# def fatality_rate(conn: Connection):
#     # Based on:
#     # https: // www.kaggle.com/alexgude/switrs-increase-in-traffic-fatalities-after-covid
#     fatalityQuery = f"""
#         SELECT collision_date
#             , 1 as crashes
#             , IIF(COLLISION_SEVERITY='fatal', 1, 0) as fatalitiesCount
#         FROM collisions 
#         WHERE collision_date IS NOT NULL 
#         AND date(collision_date) BETWEEN date('2019-01-01') AND date('2021-12-31')
#         """
#     fatalityRateDF = pd.read_sql_query(fatalityQuery, conn, parse_dates=[
#         "collision_date"]).groupby('collision_date').agg('sum')

#     return fatalityRateDF

@st.cache(hash_funcs={Connection: id}, allow_output_mutation=True, suppress_st_warning=True)
def build_dashboard(conn: Connection, start_date, end_date, specificCountyFilter, alcoholFilter):
    
    # read the population dataset containing county names
    populationData = pd.read_csv(
        'california_population_data.csv', index_col=[0])

    # function to retrieve county names
    def retrieveCountyName(dict, search_age):
        for code, county in dict.items():
            if county == search_age:
                return code

    df = get_data(conn)

    ###########
    # Filters #
    ###########

    dateMask = (df['collision_date'].dt.date >= start_date) & (
        df['collision_date'].dt.date <= end_date)

    if specificCountyFilter =='All Counties':
        countyMask = (pd.IndexSlice[slice(None)])
    else:
        countyMask = (df['county_code'] == retrieveCountyName(
            countyCodes, specificCountyFilter))

    if alcoholFilter == True:
        alcoholMask = (df['alcohol_involved'] == 1)
    else:
        alcoholMask = (pd.IndexSlice[slice(None)])

    maskedDF = df.loc[dateMask].loc[countyMask].loc[alcoholMask]

    # partyMask = (maskedDF['pedestrian_collision'] == involvedPartyPedestrian) | \
    #     (maskedDF['truck_collision'] == involvedPartyTruck) | \
    #     (maskedDF['bicycle_collision'] == inolvedPartyBike) | \
    #     (maskedDF['motorcycle_collision'] == involvedPartyMotorcycle)
    ###################
    # Fatalities per  #
    # 1000 population #
    ###################

    fatalitiesPer1000 = (maskedDF['killed_victims'].sum())/1000

    ###################
    # Injuries per    #
    # 1000 population #
    ###################

    injuriesPer1000 = (maskedDF['injured_victims'].sum())/1000
    
    #########################
    # Number of             #
    # pedestrian fatalities #
    #########################
    
    pedF = maskedDF['pedestrian_killed_count'].sum()
    
    #######################
    # Number of           #
    # injured pedestrians #
    #######################
    
    pedI = maskedDF['pedestrian_injured_count'].sum()

    ########################
    # Number of            #
    # bicyclist fatalities #
    ########################

    cyF = maskedDF['bicyclist_killed_count'].sum()

    ######################
    # Number of          #
    # injured bicyclists #
    ######################

    cyI = maskedDF['bicyclist_injured_count'].sum()

    #######
    # Map #
    #######
    
    mapDF = maskedDF[['latitude', 'longitude']].dropna().drop_duplicates()

    ################
    # Hourly graph #    
    ################
    
    maskedDF['collision_hour'] = pd.to_datetime(
        maskedDF['collision_time'], format='%H:%M:%S').dt.hour
    hourlyInjuredDF = pd.DataFrame(maskedDF.groupby('collision_hour').sum(
    )['severe_injury_count']).rename(columns={'severe_injury_count': "Number of severely injured"})
    hourlyFatalitiesDF = pd.DataFrame(maskedDF.groupby('collision_hour').sum(
    )['killed_victims']).rename(columns={'killed_victims': "Number of fatalities"})
    
    hourlyFig = figure(
        title="",
        x_axis_label='Hour',
        y_axis_label='Count')

    hourlyFig.xgrid.grid_line_color = None

    hourlyFig.line(hourlyInjuredDF.index,
                   hourlyInjuredDF['Number of severely injured'], legend_label='Severely injured', line_width=2, line_color="gray")
    hourlyFig.line(hourlyFatalitiesDF.index,
                   hourlyFatalitiesDF['Number of fatalities'], legend_label='Fatalities', line_width=2, line_color="red")

    ########################
    # Table of top factors #
    ########################

    topFactorsDF = (pd.DataFrame(maskedDF['pcf_violation_category'].value_counts(
        normalize=True)*100)).rename(columns={'pcf_violation_category': '% of all collisions'}).head(10)

    return fatalitiesPer1000, injuriesPer1000, pedF, pedI, cyF, cyI, mapDF, hourlyFig, topFactorsDF

    # fatalityDF = fatality_rate(conn)
    # fatalityDateMask = (fatalityDF.index.date >= start_date) & (
    #     fatalityDF.index.date <= end_date)
        # weeklyFatalityRateDF = fatalityDF.loc[fatalityDateMask].resample(
        #     'W-MON').sum()
        # weeklyFatalityRateDF['fatalitiesRate'] = weeklyFatalityRateDF['fatalitiesCount'] / \
        #     weeklyFatalityRateDF['crashes']
        # meanWeeklyFatalityRate = np.mean(
        #     weeklyFatalityRateDF['fatalitiesRate'])*100
        # strMWFRate = "{:.2f}%".format(meanWeeklyFatalityRate)
        # st.subheader(strMWFRate)

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












