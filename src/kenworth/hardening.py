RECOMMENDATIONS = {
    'H01': ('Alta propuesta: activo crítico y permiso amplio sin registro', 'Revisar y acotar R02 por origen, destino, servicio y vigencia; habilitar registro.', 'Comprobar flujo autorizado y registros antes y después.', 'Restaurar regla aprobada si se interrumpe un flujo legítimo.'),
    'H02': ('Alta propuesta: administración de DB-LAB sin MFA y con cuentas compartidas', 'Planificar MFA y cuentas individuales para administración.', 'Probar acceso nominal, MFA y procedimiento de recuperación.', 'Restablecer acceso administrativo aprobado bajo control de cambios.'),
    'H05': ('Alta propuesta: respaldo crítico sin evidencia de restauración', 'Programar y documentar prueba de restauración de BACKUP-LAB.', 'Registrar resultado, tiempo y consistencia de la restauración.', 'Conservar copia y procedimiento previo; detener prueba ante impacto operativo.'),
}


def plan(findings):
    return [{'hallazgo': row['hallazgo_id'], 'activo': row['activo'], 'evidencia': row['evidencia'], 'prioridad': RECOMMENDATIONS[row['hallazgo_id']][0], 'accion': RECOMMENDATIONS[row['hallazgo_id']][1], 'responsable': 'Por asignar', 'validacion': RECOMMENDATIONS[row['hallazgo_id']][2], 'reversion': RECOMMENDATIONS[row['hallazgo_id']][3]} for row in findings if row['hallazgo_id'] in RECOMMENDATIONS]
