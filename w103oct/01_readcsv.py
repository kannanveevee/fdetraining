import csv

total = 0
high_value = []

with open('data\\homework_invoices.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile)
    header = next(csvreader)
    for row in csvreader:
        total += 1
        try:
            print(f"Processing row: {row}")
            if float(row[2]) > 100000:
                high_value.append(row)
        except Exception as e:
            print(f"Error processing row {row}: {e}")

with open('data\\high_value_invoice.csv', 'w', newline='') as outfile:
    csvwriter = csv.writer(outfile)
    csvwriter.writerow(header)
    csvwriter.writerows(high_value)

print(f"Total invoices read: {total}")
print(f"Invoices greater than 100000: {len(high_value)}")
