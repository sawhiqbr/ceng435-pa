import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def read_data_from_line(file_path):
    """
    Reads a single line of comma-separated values from a file and returns them as a list.
    """
    with open(file_path, 'r') as file:
        line = file.readline()
        values = [float(val) for val in line.split(', ')]
    return values

def calculate_statistics(data):
    """
    Calculate mean and 95% confidence interval.
    """
    mean = np.mean(data)
    ci = 1.96 * np.std(data, ddof=1) / np.sqrt(len(data))
    return mean, ci

def plot_data(udp_data, tcp_data):
    """
    Plots a combined graph of individual value comparisons and overall statistics.
    """
    udp_mean, udp_ci = calculate_statistics(udp_data)
    tcp_mean, tcp_ci = calculate_statistics(tcp_data)
    
    plt.figure(figsize=(15, 8))
    
    # Plotting individual values
    plt.plot(udp_data, color='blue', label='UDP Values', marker='o')
    plt.plot(tcp_data, color='red', label='TCP Values', marker='x')

    # Plotting mean and CI
    udp_mean_index = len(udp_data)
    tcp_mean_index = udp_mean_index + 2  # Adding extra space for TCP Mean
    plt.errorbar(x=[udp_mean_index], y=[udp_mean], yerr=[udp_ci], fmt='o', color='blue', capsize=5, label='UDP Mean and 95% CI')
    plt.errorbar(x=[tcp_mean_index], y=[tcp_mean], yerr=[tcp_ci], fmt='o', color='red', capsize=5, label='TCP Mean and 95% CI')

    plt.title('Comparison of UDP vs TCP: Individual Values and Mean with 95% CI')
    plt.xlabel('Experiment Number')
    plt.ylabel('Time')
    plt.xticks(range(len(udp_data) + 2), labels=[*range(1, len(udp_data) + 1), 'UDP', 'TCP Mean'])
    plt.legend()
    plt.grid(True)
    plt.show()



def main():
    udp_file = 'udp-bmrk.csv'  # Replace with your actual UDP file path
    tcp_file = 'tcp-bmrk.csv'  # Replace with your actual TCP file path

    udp_data = read_data_from_line(udp_file)
    tcp_data = read_data_from_line(tcp_file)

    plot_data(udp_data, tcp_data)

if __name__ == "__main__":
    main()
