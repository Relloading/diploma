import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from glob import glob
from collections import defaultdict


def collect_data(directories):
    file_data = defaultdict(list)

    for directory in directories:
        csv_files = glob(os.path.join(directory, "*.csv"))

        for file_path in csv_files:
            file_name = os.path.basename(file_path)

            try:
                df = pd.read_csv(file_path)

                expected_columns = [
                    "time",
                    "time_minutes",
                    "temperature",
                    "humidity",
                    "light",
                ]
                if all(col in df.columns for col in expected_columns):
                    file_data[file_name].append(df)
            except Exception as e:
                print(f"Ошибка при чтении файла {file_path}: {e}")

    return file_data


def minutes_to_hours(minutes):
    return minutes / 60.0


def calculate_average_data(dataframes):
    if not dataframes:
        return None

    if all(
        df["time_minutes"].equals(dataframes[0]["time_minutes"]) for df in dataframes
    ):
        avg_data = dataframes[0].copy()

        avg_data["time_hours"] = avg_data["time_minutes"].apply(minutes_to_hours)

        for metric in ["temperature", "humidity", "light"]:
            avg_data[metric] = np.mean([df[metric].values for df in dataframes], axis=0)
    else:
        all_times_minutes = sorted(
            set(time for df in dataframes for time in df["time_minutes"].values)
        )
        all_times_hours = [minutes_to_hours(min) for min in all_times_minutes]

        avg_data = pd.DataFrame(
            {"time_minutes": all_times_minutes, "time_hours": all_times_hours}
        )

        for metric in ["temperature", "humidity", "light"]:
            interpolated_values = []

            for df in dataframes:
                interp_values = np.interp(
                    all_times_minutes, df["time_minutes"], df[metric]
                )
                interpolated_values.append(interp_values)

            avg_data[metric] = np.mean(interpolated_values, axis=0)

    return avg_data


def plot_comparative_data(file_name, data_set1, data_set2, label1, label2):
    plt.figure(figsize=(15, 12))

    plt.subplot(3, 1, 1)
    if data_set1 is not None:
        plt.plot(data_set1["time_hours"], data_set1["temperature"], "b-", label=label1)
    if data_set2 is not None:
        plt.plot(data_set2["time_hours"], data_set2["temperature"], "r-", label=label2)
    plt.title(f"Сравнение температуры - {file_name}")
    plt.ylabel("Температура")
    plt.xlabel("Время (часы)")
    plt.xlim(0, 24)
    plt.xticks(np.arange(0, 25, 2))
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 1, 2)
    if data_set1 is not None:
        plt.plot(data_set1["time_hours"], data_set1["humidity"], "b-", label=label1)
    if data_set2 is not None:
        plt.plot(data_set2["time_hours"], data_set2["humidity"], "r-", label=label2)
    plt.title(f"Сравнение влажности - {file_name}")
    plt.ylabel("Влажность (%)")
    plt.xlabel("Время (часы)")
    plt.xlim(0, 24)
    plt.xticks(np.arange(0, 25, 2))
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 1, 3)
    if data_set1 is not None:
        plt.plot(data_set1["time_hours"], data_set1["light"], "b-", label=label1)
    if data_set2 is not None:
        plt.plot(data_set2["time_hours"], data_set2["light"], "r-", label=label2)
    plt.title(f"Сравнение освещения - {file_name}")
    plt.xlabel("Время (часы)")
    plt.ylabel("Освещение")
    plt.xlim(0, 24)
    plt.xticks(np.arange(0, 25, 2))
    plt.grid(True)
    plt.legend()

    plt.tight_layout()
    plt.savefig(f"comparison_{file_name.replace('.csv', '')}.png")
    plt.close()

    print(
        f"Сравнительный график сохранен: comparison_{file_name.replace('.csv', '')}.png"
    )


def main():
    directories1 = [
        "/home/yeloki/diploma/reports/day_1_20250516_184148",
        "/home/yeloki/diploma/reports/day_2_20250516_184333",
        "/home/yeloki/diploma/reports/day_3_20250516_184517",
        "/home/yeloki/diploma/reports/day_4_20250516_184701",
        "/home/yeloki/diploma/reports/day_5_20250516_184845",
        "/home/yeloki/diploma/reports/day_6_20250516_185029",
    ]

    directories2 = [
        "/home/yeloki/diploma/reports/day_7_20250516_185213",
        "/home/yeloki/diploma/reports/day_8_20250516_185440",
        "/home/yeloki/diploma/reports/day_9_20250516_185712",
        "/home/yeloki/diploma/reports/day_10_20250516_185942",
        "/home/yeloki/diploma/reports/day_11_20250516_190214",
        "/home/yeloki/diploma/reports/day_12_20250516_190441",
    ]

    label1 = "Пользователь"

    label2 = "Персональный ассистент"

    file_data1 = collect_data(directories1)

    file_data2 = collect_data(directories2)

    all_file_names = set(file_data1.keys()).union(set(file_data2.keys()))

    for file_name in all_file_names:
        print(f"Обработка файла: {file_name}")

        avg_data1 = calculate_average_data(file_data1.get(file_name, []))

        avg_data2 = calculate_average_data(file_data2.get(file_name, []))

        plot_comparative_data(file_name, avg_data1, avg_data2, label1, label2)

    print("Обработка завершена!")


if __name__ == "__main__":
    main()
