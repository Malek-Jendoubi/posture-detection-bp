import pandas as pd
import matplotlib.pyplot as plt
import csv
from datetime import datetime


def save_df_to_csv(saved_df, tag):
    # Save csv of the data
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")  # Timestamp for the file name
    saved_df.to_csv(f'./training_data/data_tb_labeled/LOG_{now}_{tag}.csv', index=False)
    print(f"Values of LOG saved to ./training_data/LOG_{now}_{tag}.csv")


def filter_successive_ids(input_csv):
    """
    This function takes a csv of pressure values as input and filters the successive values that have the same id.

    Parameters:
    input_csv: string containing the path to a csv containing duplicate values of id 

    Returns:
    df (pd.DataFrame): DataFrame containing the filtered values with columns 'id, timestamp, pressure_values'
    """
    with open(input_csv, mode='r') as infile, open('./LOG_CROPPED.csv', mode='w', newline='') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        buffer = []
        
        for row in reader:
            buffer.append(row)
            # Only keep the last three rows in the buffer
            if len(buffer) > 3:
                buffer.pop(0)
            
            # Check if the buffer contains the sequence [1, 2, 3]
            if len(buffer) == 3:
                    if [r['id'] for r in buffer] == ['1', '2', '3']:
                        for b_row in buffer:
                            writer.writerow(b_row)
                        buffer = []
    
    return pd.read_csv('./LOG_CROPPED.csv')


def pressure_to_elevation_m(pressure_Pa):
    """
    This function takes a pressure_values and converts it to an elevation value using the atmospheric formula.

    Parameters:
    pressure_Pa: integer of a pressure value.

    Returns:
    h_cm: integer of an elevation value in cm
    """
    pressure_hPa = pressure_Pa / 100
    # Constants
    P0 = 1013.25  # sea level standard atmospheric pressure in hPa
    L = 0.0065    # temperature lapse rate in K/m
    T0 = 288.15   # sea level standard temperature in K
    g = 9.80665   # acceleration due to gravity in m/s^2
    M = 0.0289644 # molar mass of Earth's air in kg/mol
    R = 8.31432   # universal gas constant in N·m/(mol·K)

    # Calculate the exponent
    exponent = (R * L) / (g * M)
    
    # Calculate the height in meters
    h_m = (T0 / L) * (1 - (pressure_hPa / P0) ** exponent)
    
    # Convert the height to centimeters
    h_cm = h_m * 100
    
    return int(h_cm)
    # return int(h_m)


def preprocess_df_pressure(in_csv):
    out_data = filter_successive_ids(in_csv)
       
    # Preprocessing the data before plotting
    out_data.astype(int)
    
    # subtract from the reading of device 3. Measurement correction done after calibration.
    out_data.loc[out_data['id'] == 3, 'pressure_values'] -= 25
    
    # Subtract from pressure value at sea level
    out_data['pressure_values'] = 101325 - out_data['pressure_values']
    
    return out_data


def preprocess_df_elevation(in_csv):
    out_data = filter_successive_ids(in_csv)
       
    # Preprocessing the data before plotting
    out_data.astype(int)
    
    # subtract from the reading of device 3. Measurement correction done after calibration.
    out_data.loc[out_data['id'] == 3, 'pressure_values'] -= 25
    out_data['elevation_value'] = out_data['pressure_values'].apply(pressure_to_elevation_m)
    out_data = out_data.drop(columns=['pressure_values'])
   
    return out_data


def plot_pressure_data(plot_df):
    """
    This function takes a DataFrame of pressure values as input and plots the values.

    Parameters:
    df (pd.DataFrame): DataFrame containing columns 'id, timestamp, pressure_values'

    Returns:
    None
    """
    # Plot data for each id
    unique_ids = plot_df['id'].unique()
    
    for unique_id in unique_ids:
        subset = plot_df[plot_df['id'] == unique_id]
        plt.plot(subset['timestamp'], subset['pressure_values'], label=f'DEV{unique_id}')

    # Plot the elevation Data
    plt.title(f'Measurements of Elevation\n')
    plt.ylabel("Elevation Value")
    plt.xlabel("Time in ms")
    plt.legend(loc="center")
    plt.show()


def plot_elevation_data(plot_df):
    """
    This function takes a DataFrame of elevation values as input and plots the values.

    Parameters:
    df (pd.DataFrame): DataFrame containing columns 'id, timestamp, elevation_value'

    Returns:
    None
    """
    # Plot data for each id
    unique_ids = plot_df['id'].unique()
    
    for unique_id in unique_ids:
        subset = plot_df[plot_df['id'] == unique_id]
        plt.plot(subset['timestamp'], subset['elevation_value'], label=f'DEV{unique_id}')

    # Plot the elevation Data
    plt.title(f'Measurements of Elevation\n')
    plt.ylabel("Elevation Value")
    plt.xlabel("Time in ms")
    plt.legend(loc="center")
    plt.show()


def calculate_deltas_elevation(data_frame):
    """
    This function takes a DataFrame of elevation values with header 'id, timestamp, elevation_value' as input,
    calculates the difference in elevation
    and returns a new Df with an index and delta values.

    Parameters:
    df (pd.DataFrame): DataFrame containing columns 'id, timestamp, elevation_value'

    Returns:
    df (pd.DataFrame): DataFrame containing columns 'index, delta3_1 , delta3_2, delta2_1'
    """
    results = []
    for i in range(len(data_frame) - 2):
        subset = data_frame.iloc[i:i + 3]
        if subset['id'].nunique() == 3:
            # Calculate the differences between their elevation values
            elevation_value = subset.set_index('id')['elevation_value']
            delta3_1 = elevation_value[3] - elevation_value[1]
            delta3_2 = elevation_value[3] - elevation_value[2]
            delta2_1 = elevation_value[2] - elevation_value[1]

            # Append the result
            results.append([i, delta3_1, delta3_2, delta2_1])
    
    # Convert the results to a DataFrame
    deltas_df = pd.DataFrame(results, columns=['index', 'delta3_1', 'delta3_2', 'delta2_1'])

    return deltas_df


def plot_deltas(deltas_df):
    """
    This function takes a DataFrame of elevation deltas as input and plots the values.

    Parameters:
    df (pd.DataFrame): DataFrame containing columns 'index', 'delta3_1', 'delta3_2', and 'delta2_1'

    Returns:
    None
    """
    # Set 'index' column as the index for plotting
    deltas_df.set_index('index', inplace=True)

    # Plot each column
    plt.figure(figsize=(10, 6))
    plt.plot(deltas_df.index, deltas_df['delta3_1'], label='delta3_1', color='r')
    plt.plot(deltas_df.index, deltas_df['delta3_2'], label='delta3_2', color='b')
    plt.plot(deltas_df.index, deltas_df['delta2_1'], label='delta2_1', color='g')

    plt.title('Values of delta3_1, delta3_2, and delta2_1')
    plt.xlabel('Index')
    plt.ylabel('Values')

    plt.legend()
    plt.grid(True)
    plt.show()


def label_based_on_timestamp(elevation_delta_df, time_ranges):
    """
    Function to label the DataFrame based on timestamp ranges

    Parameters:
    df (pd.DataFrame): DataFrame containing columns 'index, delta3_1, delta3_2, delta2_1'

    Returns:
    df (pd.DataFrame): DataFrame containing columns 'index, delta3_1, delta3_2, delta2_1, label'
    """
    # Initialize the label column with default value
    elevation_delta_df['label'] = 'undefined'

    # Iterate over the ranges and apply labels
    for start, end, label in time_ranges:
        elevation_delta_df.loc[(elevation_delta_df['avg_timestamp'] >= start) & (elevation_delta_df['avg_timestamp'] <= end), 'label'] = label

    return elevation_delta_df


def calculate_mean_variance(df):
    # Calculate rolling mean and standard deviation
    window_size = 10
    df['delta3_1_mean'] = df['delta3_1'].rolling(window=window_size).mean()
    df['delta3_2_mean'] = df['delta3_2'].rolling(window=window_size).mean()
    df['delta2_1_mean'] = df['delta2_1'].rolling(window=window_size).mean()
    df['delta3_1_std'] = df['delta3_1'].rolling(window=window_size).std()
    df['delta3_2_std'] = df['delta3_2'].rolling(window=window_size).std()
    df['delta2_1_std'] = df['delta2_1'].rolling(window=window_size).std()

    return df


# Pre-process data
df_elevation = preprocess_df_elevation('training_data/Measurements_01/LOG_2024-07-25_14-09_laystandsitstand.csv')
# Calculate deltas
deltas_elevation = calculate_deltas_elevation(df_elevation)

plot_deltas(deltas_elevation)

