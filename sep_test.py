import pandas as pd
df = pd.read_csv('ZE18_1000_CL.csv', header=0)  # header=0 означает, что первая строка - заголовки

# Разделение данных
df_part1 = df[df['Time (s)'] <= 119.6].copy()
df_part2 = df[df['Time (s)'] >= 120].copy()

# Перезапись времени с нуля
df_part1['Time (s)'] = df_part1['Time (s)'] - df_part1['Time (s)'].iloc[0]
df_part2['Time (s)'] = round(df_part2['Time (s)'] - df_part2['Time (s)'].iloc[0],2)

# Сохранение в CSV
df_part1.to_csv('ZE18_1000_CL_as.csv', index=False)
df_part2.to_csv('ZE18_1000_CL_dis.csv', index=False)

