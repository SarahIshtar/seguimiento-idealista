import pandas as pd
import openpyxl


##Convertir el excel a csv
df = pd.read_excel('Seguimiento Idealista.xlsx', sheet_name='Recopilación tratados') 
df['Enlace'] = df['Enlace'].str.strip()
df.to_csv('Seguimiento Idealista.csv', index=False, encoding='utf-8-sig')

