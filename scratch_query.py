import sqlite3
con = sqlite3.connect('db/gansos.db')
cur = con.cursor()
cur.execute("DELETE FROM vendas WHERE arquivo_origem='AppBarber  Relatório Gerencial Financeiro (11).xlsx'")
print('Linhas deletadas do arquivo 11:', cur.rowcount)
con.commit()
