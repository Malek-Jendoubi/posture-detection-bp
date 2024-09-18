import asyncio
import contextlib
import logging
import csv
import pandas as pd

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

from build_csv import *

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


def build_csv():
    # Build a csv from the file of raw data

    with open("./RAW_LOG.csv", "r") as source_file, open("./LOG.csv", "w") as destination_file:

        # write csv header
        destination_file.writelines("id,timestamp,pressure_values\n")

        lines = source_file.readlines()

        # Write 1 line, skip 2 (garbage values in these lines)
        index = 0
        while index < len(lines):
            destination_file.write(lines[index])
            index += 2

        destination_file.close()
        source_file.close()

    print(f"LOG saved to: ./LOG.csv")


def write_to_file(str_value=None):
    file = open("./RAW_LOG.csv", "a")
    file.writelines(str_value)
    file.writelines("\n")
    file.close()


def save_csv(tag: str, df):
    # Save df to csv file
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")  # Timestamp for the file name
    filepath = f'./csv/LOG_{now}_{tag}.csv'
    df.to_csv(filepath, index=False)
    print(f"Values of LOG saved to ./csv/LOG_{now}_{tag}.csv")

    return filepath


async def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
    """Simple notification handler which prints the data received."""
    try:
        sensor_value: str = data.decode('ascii')
    except UnicodeDecodeError:
        return
    else:
        write_to_file(str(sensor_value))
        return


async def connect_to_device(lock: asyncio.Lock, name_or_address: str,
                            notify_uuid: str, log_duration: int):
    """
    Scan and connect to a device then print notifications for a duration
    log_duration before disconnecting.

    Args:
        lock:
            The same lock must be passed to all calls to this function.
        name_or_address:
            The Bluetooth address/UUID of the device to connect to.
        notify_uuid:
            The UUID of a characteristic that supports notifications.
        log_duration:
            Duration of the logging session
    """
    logging.info("starting %s task", name_or_address)

    try:
        async with contextlib.AsyncExitStack() as stack:

            # Trying to establish a connection to two devices at the same time
            # can cause errors, so use a lock to avoid this.
            async with lock:
                print(f"scanning for {name_or_address}")

                device = await BleakScanner.find_device_by_name(name_or_address)

                print(f"stopped scanning for {name_or_address}")

                if device is None:
                    logging.error("%s not found", name_or_address)
                    return

                client = BleakClient(device)

                print(f"connecting to {name_or_address}")

                await stack.enter_async_context(client)

                print(f"connected to {name_or_address}", name_or_address)

                # This will be called immediately before client.__aexit__ when
                # the stack context manager exits.
                stack.callback(logging.info, "disconnecting from %s", name_or_address)

            await client.start_notify(notify_uuid, notification_handler)
            await asyncio.sleep(log_duration)
            await client.stop_notify(notify_uuid)

            # The lock is released here. The device is still connected and the
            # Bluetooth adapter is now free to scan and connect another device
            # without disconnecting this one.

        # The stack context manager exits here, triggering disconnection.

        print(f"disconnected from {name_or_address}")

    except Exception:
        logging.exception("error with %s", name_or_address)


async def bmp581_client():
    valid_input = False
    log_duration = 0

    while not valid_input:
        try:
            log_duration = int(input("Enter the desired log duration in seconds:"))
            valid_input = True
        except ValueError:
            print("Invalid input. Please enter a valid log duration. 0 to take the data from Log.csv\n")
            valid_input = False
    tag = input("Enter the desired logging tag:")

    if log_duration == 0:
        return -1

    print(f"log_duration={log_duration} seconds with tag {tag}.")

    # cf. bt-periph.h mysensor char uuid
    char_pres_uuid = "75c276c4-8f97-20bc-a143-b354244886d4"

    open("./RAW_LOG.csv", "w")
    print("Looking for devices...")

    device_ids = ["DEV001", "DEV002", "DEV003"]

    lock = asyncio.Lock()

    await asyncio.gather(
        *(
            connect_to_device(lock, address, char_pres_uuid, log_duration)
            for address in device_ids
        )
    )

    print(f"LOG_RAW.csv saved.")
    build_csv()

    df = preprocess_df('./LOG.csv', './LOG_CROPPED.csv')

    filepath = save_csv(tag, df)
    print(f"{filepath} saved.")

    return 0


if __name__ == "__main__":
    result: int = asyncio.run(bmp581_client())

