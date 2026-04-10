TABLE_FILTER_SCHEMA = {
    "medications": {
        "table_aliases": [
            "medicacion", "medicaciones", "medicado", "medicados",
            "tratamiento", "tratamientos"
        ],
        "columns": {
           "Fecha_inicio": {
                "type": "date",
                "aliases": [
                    "medicandose desde",
                    "lleven medicandose desde",
                    "lleva medicandose desde",
                    "tratamiento desde",
                    "medicado desde",
                    "medicados desde",
                    "tomando desde",
                    "desde",
                    "fecha inicio"
                ]
            },
            "Fecha_fin": {
                "type": "date",
                "aliases": ["hasta", "fecha fin"]
            },
            "Nombre": {
                "type": "text",
                "aliases": ["medicacion", "medicamento", "farmaco", "nombre"]
            },
            "Via_administracion": {
                "type": "text",
                "aliases": ["via", "via de administracion"]
            },
        },
    },
    "encounters": {
        "table_aliases": [
            "encuentro", "encuentros", "visita", "visitas", "consulta", "consultas"
        ],
        "columns": {
            "Tipo_encuentro": {
                "type": "text",
                "aliases": ["tipo de encuentro", "tipo encuentro", "encuentro de"]
            },
            "Fecha_inicio": {
                "type": "date",
                "aliases": ["encuentros desde", "visitas desde", "desde", "fecha inicio"]
            },
            "Fecha_fin": {
                "type": "date",
                "aliases": ["encuentros hasta", "visitas hasta", "hasta", "fecha fin"]
            },
        },
    },
    "allergies": {
        "table_aliases": [
            "alergia", "alergias", "alergico", "alergicos"
        ],
        "columns": {
            "Fecha_diagnostico": {
                "type": "date",
                "aliases": ["diagnosticada desde", "diagnosticados desde", "fecha diagnostico"]
            },
            "Descripcion": {
                "type": "text",
                "aliases": ["alergia a", "descripcion"]
            },
        },
    },
}