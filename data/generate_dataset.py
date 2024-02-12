import random
import csv

# Define the number of examples and the range of trend sizes
num_examples = 100
min_trend_size = 50
max_trend_size = 150

# Define the output file
with open('training_data.csv', 'w', newline='') as file:
    writer = csv.writer(file)

    # Write header
    header = ["trend_type", "trend"]
    writer.writerow(header)

    # Generate 'leaking' trends
    for _ in range(num_examples):
        trend_size = random.randint(min_trend_size, max_trend_size)
        start = random.randint(50, 100)
        trend = [str(start + i) for i in range(trend_size)]
        writer.writerow(["leaking", ",".join(trend)])

    # Generate 'normal' trends
    for _ in range(num_examples):
        trend_size = random.randint(min_trend_size, max_trend_size)
        value = random.randint(50, 100)
        trend = [str(value) for _ in range(trend_size)]
        writer.writerow(["normal", ",".join(trend)])

    # Generate 'sawtooth' trends
    for _ in range(num_examples):
        trend_size = random.randint(min_trend_size, max_trend_size)
        start = random.randint(50, 100)
        trend = [str((start + i) % 100) for i in range(trend_size)]
        writer.writerow(["sawtooth", ",".join(trend)])