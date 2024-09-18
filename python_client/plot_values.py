from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import csv

'''
    TODO: Overhaul plotter using plotly.
    Sorted data with timestamp

'''


def filter_successive_ids(input_csv):
    with open(input_csv, mode='r') as infile, open('./LOG_CROPPED.csv', mode='w', newline='') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        print(reader)
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


def preprocess_df(in_csv, out_csv):
    filter_successive_ids(in_csv)
    data = pd.read_csv(out_csv)

    # Preprocessing the data before plotting
    data.astype(int)

    # Remove 33 from the reading of device 3. Measurement correction done after calibration.
    data.loc[data['id'] == 3, 'pressure_values'] -= 19
    data.loc[data['id'] == 2, 'pressure_values'] -= 0
    data.loc[data['id'] == 1, 'pressure_values'] -= 0

    # display(data)

    return data


def plot_sensor_data(plot_df):
    # Subtract from Air Pressure Value at ground level
    plot_df['pressure_values'] = 101325 - plot_df['pressure_values']

    # Plot data for each id
    unique_ids = plot_df['id'].unique()

    for unique_id in unique_ids:
        subset = plot_df[plot_df['id'] == unique_id]
        plt.plot(subset['timestamp'], subset['pressure_values'], label=f'DEV{unique_id}')

    # Plot the elevation Data
    plt.title(f'Measurements of Pressure (Pa)\n')
    plt.ylabel("Pressure Measure / Pressure at sea level (101325 Pa)")
    plt.xlabel("Time in ms")

    plt.legend(loc="center")

    # Save the figure as PNG
    # plt.savefig(f"./figures/FIGURE_{now}.PNG", dpi=1000)
    # print(f"Figure saved to ./LOG_{now}.PNG")

    # Show the figure
    plt.show()


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
    L = 0.0065  # temperature lapse rate in K/m
    T0 = 288.15  # sea level standard temperature in K
    g = 9.80665  # acceleration due to gravity in m/s^2
    M = 0.0289644  # molar mass of Earth's air in kg/mol
    R = 8.31432  # universal gas constant in N·m/(mol·K)

    # Calculate the exponent
    exponent = (R * L) / (g * M)

    # Calculate the height in meters
    h_m = (T0 / L) * (1 - (pressure_hPa / P0) ** exponent)

    # Convert the height to centimeters
    h_cm = h_m * 100

    return int(h_cm)
    # return int(h_m)


def plot_elevation_data(plot_df):
    plot_df['elevation_value'] = plot_df['pressure_values'].apply(pressure_to_elevation_m)
    plot_df = plot_df.drop(columns=['pressure_values'])

    # Plot data for each id
    unique_ids = plot_df['id'].unique()

    for unique_id in unique_ids:
        subset = plot_df[plot_df['id'] == unique_id]
        plt.plot(subset['timestamp'], subset['elevation_value'], label=f'DEV{unique_id}')

    # Plot the elevation Data
    plt.title(f'Measurements of Elevation\n')
    plt.ylabel("Elevation Measure")
    plt.xlabel("Time in ms")

    plt.legend()

    # Show the figure
    plt.show()


def plot_values(tag: str):
    in_csv = './LOG.csv'
    out_csv = './LOG_CROPPED.csv'
    df = preprocess_df(in_csv, out_csv)

    # Save df to csv file
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")  # Timestamp for the file name
    df.to_csv(f'./csv/LOG_{now}_{tag}.csv', index=False)
    print(f"Values of LOG saved to ./csv/LOG_{now}_{tag}.csv")

    plot_sensor_data(df)
    # plot_elevation_data(df)


if __name__ == "__main__":
    plot_values("Test")
