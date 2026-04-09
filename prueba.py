
# hazme una consulta al archivo cohorte_alegies.csv para obtener el numero de pacientes con alergia.
import pandas as pd

df = pd.read_csv("cohorte_alegias.csv")
print(df["PacienteID"].nunique())