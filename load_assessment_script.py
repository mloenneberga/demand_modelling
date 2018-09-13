import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# initialize empty pd.Dataframe for dayloads (day_ld) and annual loads (annual_ld)
day_ld = pd.DataFrame()
annual_ld = pd.DataFrame()

# read input files cl (cluster data) / ld (load profiles)
input_file = 'inputs.xlsx'
cluster_table = 'merged-mini-grid-cluster-prio.xlsx'

cl_df = pd.read_excel(input_file,
                      sheet_name='load_params',
                      dtype={'description': str,
                             'unit': str},
                      index_col='parameter'
                      )

ld_df = pd.read_excel(input_file,
                      sheet_name='load_profiles',
                      )

# read cluster list into pd.DataFrame


cluster_df = pd.read_excel(cluster_table,
                           sheet_name='merged-mini-grid-cluster-prio',
                           dtype={'building': int, 'no_schools': int},
                           index_col='ID')


# plot function for load profiles
def plot_load_profiles(profile_df=ld_df):
    ax = profile_df.plot()
    ax.set_xlabel('hour of the day')
    ax.set_ylabel('share of load')
    plt.show()


# make a copy of the index_column and the value_column --> cv cluster values
cl_v = cl_df['value'].copy()

# define params that are considered in a list (Households excluded)
params_list = ['SC', 'WP', 'PU', 'AGR', 'HFL', 'HFH', 'CU']

# loop over list and calculate daily profile per parameter type, store result in column of day_ld

# daily load generated via params_list
for id in params_list:
    try:
        day_ld[id] = cl_v['no_' + id] * cl_v['consume_' + id] * ld_df[id]
    except KeyError or ValueError:
        print(id + ': Error-Warning, most probably a KeyError')
        pass

# initialize results_df cluster_ld_results
cluster_ld_results = pd.DataFrame()

# loop over Cluster IDs that are stored in index-column of cluster_ld_results
for ind in cluster_df.index:

    # Household factor is defined to calculate avergae number of HH from building counts
    HH_factor = 3

    # map values from cluster_df to cl_v (fixed cluster valuues)
    cl_v['cluster_id'] = ind
    cl_v['no_HH'] = cluster_df.loc[ind, 'buildings'] / HH_factor
    cl_v['no_SC'] = cluster_df.loc[ind, 'no_schools']

    # daily load generated for households (HH)
    for kd in ['low', 'medium', 'high']:
        day_ld['HH_' + kd] = cl_v['no_HH'] * cl_v['shr_HH_connected'] * (
                cl_v['shr_HH_' + kd] * cl_v['consume_HH_' + kd] * cl_v['tariff_' + cl_v['tariff'] + '_use_HH_' + kd] *
                ld_df[
                    'HH_' + kd]
        )

    # annual_ld['dayload']: sum of dayloads per category is build (dayload_totak) and series is appended to 365 tiles of
    # 24-hour (dayload)
    annual_ld['dayload'] = np.tile(day_ld.sum(axis=1), 365)

    # covert 'location' from string to tuple
    loc = tuple(map(float, cl_v['location'].split(',')))
    # select first value of tuple --> latitude (lat)
    lat = loc[0]
    # annual seasonal variability for nothern(lat>0) and southern hemisphere (lat <=0)
    if lat <= 0:
        season_var = pd.np.zeros(8760)
        season_var[0:2919] = 0.1
        season_var[2920:3650] = 0.15
        season_var[3651:5879] = 0.1
        season_var[5880:8760] = 0.2
    elif lat > 0:
        season_var = pd.np.zeros(8760)
        season_var[0:5879] = 0.2
        season_var[5880:8030] = 0.3
        season_var[8031:8760] = 0.2
    else:
        raise (ValueError, 'check if location is properly set as lat,lon')

    # calculate annual seasonal load based on agricultural activity

    annual_ld['seasonal'] = pd.Series(
        data=season_var * np.tile(cl_v['no_AGR'] * cl_v['consume_AGR'] * day_ld['AGR'], 365))

    # calculate random variability (dtd+hth+1) including day-to-day (dtd) variability and hour-to-hour (hth) variability
    day_to_day = 0.1
    hour_to_hour = 0.05

    for p in range(365):
        annual_ld.loc[p * 24:(p + 1) * 24, 'dtd_rand'] = np.random.uniform(-1, 1) * day_to_day

    for k in range(8760):
        annual_ld.loc[k, 'hth_rand'] = np.random.uniform(-1, 1) * hour_to_hour

    annual_ld['variability'] = 1 + annual_ld['hth_rand'] + annual_ld['dtd_rand']

    # generate hourly load profile load_total
    annual_ld['load_total'] = (annual_ld['dayload'] + annual_ld['seasonal']) * annual_ld['variability']

    cluster_ld_results[ind] = annual_ld['load_total']

cluster_demand = cluster_ld_results.T.to_csv('cluster_demand.csv')
