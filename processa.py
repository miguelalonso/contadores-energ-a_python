#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
	Protocol IEC 60870-5-102
	Autor: Lluis Bosch (lbosch@icra.cat) & Felix Hill (fhill@icra.cat)

	Mòdul per traduir a nivell llegible missatges (peticions i respostes)
	Testejat amb un comptador Actaris SL761

	Exemple de com fer servir:

		import processa as Pro
		Pro.processa('\x10\x49\x01\x00\x4a\x16')


	Bibliografia: #TODO

	Els missatge provenen de la comanda serial.readlines()
	normalment sera un array de tamany 1 però pot ser més llarg

	Estructura global:

		* Processa missatge
			* trama fixe
				* camp control
			* trama variable
				* camp control
				* asdu
					* iud
					* objectes
'''
def processa(missatge):
	'''
		missatge: byte string com ara: '\x10\x49\x01\x00\x4a\x16', s'ha de passar a bytearray
	'''
	global buf #disponible a totes les funcions per agafar bits d'altres camps
	buf=bytearray(missatge)

	'''comptar numero de bytes del buffer'''
	n=len(buf) 

	print("<missatge>\n  "+str(n)+" bytes:"),

	'''mostra tots els bytes del missatge'''
	for i in range(n): print hex(buf[i])[2:4], 
	print('')
	
	'''primer pas: descobrir si la trama es fixa o variable, mirant bytes d'inici (0x10 ò 0x68) i final (0x16)'''
	if(buf[0]==0x10 and buf[n-1]==0x16):
		processaTramaFixa(buf)
	elif(buf[0]==0x68 and buf[n-1]==0x16):
		processaTramaVariable(buf)
	else:
		raise RuntimeError('Tipus de trama desconegut')

	'''fi'''
	print('</missatge>\n')

'''processa una trama de longitud fixa (sempre són 6 bytes)'''
def processaTramaFixa(buf):
	''' 
		buf: objecte bytearray

		estructura:
				6        5      4   3      2        1
		+-------+---------+-------+----------+----+
		| inici | control | direc | checksum | fi |
		+-------+---------+-------+----------+----+
	'''
	n=len(buf)

	'''comprovacions'''
	if(n!=6): raise RuntimeError('La trama no te longitud 6')

	if(buf[0]!=0x10 and buf[n-1]!=0x16): 
		raise RuntimeError('Bytes inici (0x10) i final (0x16) erronis')

	'''comprova checksum'''
	checksum = (buf[1]+buf[2]+buf[3])%256
	if(checksum==buf[4]):    
		print("  Checksum correcte ("+hex(buf[4])+"="+str(buf[4])+")")
	else:
		raise RuntimeError('Checksum incorrecte: '+str(checksum)+'=/='+str(buf[4]))

	print("  Trama de tipus FIXE [inici (0x10), control, direccio1, direccio2, checksum, fi (0x16)]")

	'''processa el byte de control'''
	control=buf[1]
	campControl(control)

	'''mostra els 2 bytes de direccio: byte swap i suma'ls'''
	direccio = buf[3] << 8 | buf[2]

	'''fi'''
	print("  Direcció comptador: "+hex(direccio)+" = "+str(direccio))

'''processa una trama de longitud variable'''
def processaTramaVariable(buf):
	'''
		buf: objecte bytearray

		estructura:

           1          1      1           1          1        2     ?        1            1
		+--------------+------+------+--------------+---------+-----+------+----------+--------------+
		| Inici (0x68) | Long | Long | Inici (0x68) | Control | A A | ASDU | Checksum | Final (0x16) |
		+--------------+------+------+--------------+---------+-----+------+----------+--------------+
	'''
	n=len(buf)

	'''comprova bytes inici i final'''
	if(buf[0]!=0x68 and buf[3]!=0x68 and buf[n-1]!=0x16): 
		raise RuntimeError("Bytes inici i final erronis")

	'''comprova que els dos bytes de longitud (Long) siguin iguals'''
	if(buf[1]!=buf[2]): 
		raise RuntimeError("Els bytes de longitud (2n i 3r) son diferents")

	'''comprova checksum (penúltim byte)'''
	checksum=0
	for i in range(4,n-2): 
		checksum += buf[i]
	checksum%=256
	if checksum == buf[n-2]: 
		print("  Checksum correcte ("+hex(buf[n-2])+"="+str(buf[n-2])+")")
	else:
		raise RuntimeError("Checksum incorrecte: "+str(buf[n-2])+"=/="+str(checksum))

	print("  La trama es de tipus VARIABLE [inici (0x68), L, L, inici (0x68), ASDU, checksum, final (0x16)]")

	'''byte de control'''
	control=buf[4]
	campControl(control)

	'''2 bytes de direccio: byte swap i suma'ls'''
	direccio = buf[6] << 8 | buf[5]
	print("  Direcció comptador: "+str(hex(direccio))+" = "+str(direccio))

	'''camp ASDU: del byte 6 fins al el n-3'''
	ASDU=buf[7:n-2]

	'''Comprova si el byte de longitud coincideix amb la suma de control+direccio+asdu'''
	if(buf[1]==1+2+len(ASDU)):
		print("  Camp longitud correcte ("+hex(buf[1])+" = "+str(buf[1])+" = "+str(len(ASDU))+"+3)")
	else:
		raise RuntimeError("Camp Longitud ("+str(buf[1])+") incorrecte")
	
	'''fi'''
	campASDU(ASDU)

'''processa el byte Control'''
def campControl(control):
	'''
		control: un byte (0-255) = 8 bits

		estructura:
			 8     7     6     5     4   3   2   1
		+-----+-----+-----+-----+-----------------+
		| RES | PRM | FCB | FCV |       FUN       | (si PRM=1)
		+-----+-----+-----+-----+-----------------+

		o bé

		+-----+-----+-----+-----+-----------------+
		| RES | PRM | ACD | DFC |       FUN       | (si PRM=0)
		+-----+-----+-----+-----+-----------------+
	'''

	print("  <control>")
	print("    Byte control: "+hex(control)+" = "+str(control)+" = "+bin(control))
	res = control & 0b10000000 == 128
	prm = control & 0b01000000 == 64
	fcb = control & 0b00100000 == 32 #tambe acd
	fcv = control & 0b00010000 == 16 #tambe dfc
	fun = control & 0b00001111
	acd = fcb
	dfc = fcv
	#print([res,prm,fcb,fcv,fun]) #debugging

	'''mostra informacio de cada part'''
	'''bit res (reserva) sempre ha de ser 0'''
	if(res): 
		raise RuntimeError("Bit de reserva no és 0")

	'''bit prm: direccio del missatge'''
	if(prm): print("    bit PRM=1: Aquest missatge es una PETICIO");
	else:    print("    bit PRM=0: Aquest missatge es una RESPOSTA");

	'''bits acd (accés permès) i dfc (data overflow)'''
	if(prm==False): 
		if(acd): 
			print("    ACD=1: Es permet l'acces a les dades de classe 1")
		else:
			print("    ACD=0: No es permet l'acces a les dades de classe 1 (ignorat per reglament REE)")

		if(dfc): 
			raise RuntimeError("    DFC = 1. ELS MISSATGES FUTURS CAUSARAN DATA OVERFLOW")

	'''Mostra el text de la funcio "fun" (4 bits) '''
	if(prm):
		print({
			 0:"    [Funció 0] [Petició: RESET DEL LINK REMOT]",
			 3:"    [Funció 3] [Petició: ENVIAMENT DE DADES D'USUARI]",
			 9:"    [Funció 9] [Petició: SOL·LICITUD DE L'ESTAT DEL LINK]",
			11:"    [Funció 11] [Petició: SOL·LICITUD DE DADES DE CLASSE 2]",
		}[fun])
	else:
		print({
			 0:"    [Funció 0] [Resposta: ACK]",
			 1:"    [Funció 1] [Resposta: NACK. COMANDA NO ACCEPTADA]",
			 8:"    [Funció 8] [Resposta: DADES DE L'USUARI]",
			 9:"    [Funció 9] [Resposta: NACK. DADES DEMANADES NO DISPONIBLES]",
			11:"    [Funció 11] [Resposta: ESTAT DEL LINK O DEMANDA D'ACCÉS]",
		}[fun])
	'''fi'''
	print("  </control>")

'''camp iud dins del camp ASDU'''
def campIUD(iud):
	'''
		iud: bytearray (6 bytes)

			 6     5     4     3   2   1
		+-----+-----+-----+-------------+
		| IDT | QEV | CDT |    DCO      |
		+-----+-----+-----+-------------+

		idt = identificador de tipus
		qev = qualificador d'estructura variable
		cdt = causa de transmissió
		dco = direcció comuna
	'''
	n=len(iud)
	print("    <iud>")
	print("      "+str(n)+" bytes: [idt, qev, cdt, dco]:"),

	'''mostra tots els bytes'''
	for i in range(n): print hex(iud[i])[2:4],
	print('')

	'''agafa els bytes'''
	idt=iud[0]
	qev=iud[1]
	cdt=iud[2]
	dco=iud[3:6]

	'''Diccionari identificadors de tipus (idt)'''
	dicc_idt={
		8  :"TOTALES INTEGRADOS OPERACIONALES, 4 OCTETOS (LECTURAS DE CONTADORES ABSOLUTOS, EN KWH O KVARH)",
		11 :"TOTALES INTEGRADOS OPERACIONALES REPUESTOS PERIÓDICAMENTE, 4 OCTETOS (INCREMENTOS DE ENERGÍA, EN KWH O KVARH)",
		71 :"IDENTIFICADOR DE FABRICANTE Y EQUIPO. EN LUGAR DE UN CODIGO DE PRODUCTO SE ENVIARA UN IDENTIFICADOR DE EQUIPO",
		72 :"FECHA Y HORA ACTUALES",
		100:"LEER IDENTIFICADOR DE FABRICANTE Y EQUIPO",
		102:"LEER REGISTRO DE INFORMACIÓN DE EVENTO (SINGLE-POINT) POR INTERVALO DE TIEMPO",
		103:"LEER FECHA Y HORA ACTUALES",
		122:"LEER TOTALES INTEGRADOS OPERACIONALES POR INTERVALO DE TIEMPO Y RANGO DE DIRECCIONES",
		123:"LEER TOTALES INTEGRADOS OPERACIONALES REPUESTOS PERIÓDICAMENTE POR INTERVALO DE TIEMPO Y RANGO DE DIRECCIONES",
		128:"FIRMA ELECTRÓNICA DE LOS TOTALES INTEGRADOS (LECTURAS)",
		129:"PARÁMETROS DEL PUNTO DE MEDIDA",
		130:"FIRMA ELECTRÓNICA DE LOS TOTALES INTEGRADOS REPUESTOS PERIÓDICAMENTE (INCREMENTOS DE ENERGÍA)",
		131:"FECHAS Y HORAS DE CAMBIO DE HORARIO OFICIAL",
		132:"CARGA DE CLAVE PRIVADA DE FIRMA",
		133:"LEER INFORMACIÓN DE TARIFICACIÓN (VALORES EN CURSO)",
		134:"LEER INFORMACIÓN DE TARIFICACIÓN (VALORES MEMORIZADOS)",
		135:"INFORMACIÓN DE TARIFICACIÓN (VALORES EN CURSO)",
		136:"INFORMACIÓN DE TARIFICACIÓN (VALORES MEMORIZADOS)",
		137:"CERRAR PERÍODO DE FACTURACIÓN",
		138:"RESERVADO PARA VERSIONES FUTURAS DEL PROTOCOLO RM-CM",
		139:"BLOQUES DE TOTALES INTEGRADOS OPERACIONALES (LECTURAS DE CONTADORES ABSOLUTOS, EN KWH O KVARH)",
		140:"BLOQUES DE TOTALES INTEGRADOS OPERACIONALES REPUESTOS DE ENERGÍA PERIÓDICAMENTE (INCREMENTOS DE ENERGÍA EN KWH O KVARH)",
		141:"LEER LA CONFIGURACIÓN DEL EQUIPO RM.",
		142:"ENVÍO DE LA CONFIGURACIÓN DEL EQUIPO RM.",
		143:"MODIFICACIÓN DE LA CONFIGURACIÓN DE LOS PUERTOS DE COMUNICACIONES.",
		144:"LECTURA DE POTENCIAS DE CONTRATO.",
		145:"ENVÍO DE POTENCIAS DE CONTRATO.",
		146:"MODIFICACIÓN DE POTENCIAS DE CONTRATO.",
		147:"LECTURAS DE DÍAS FESTIVOS.",
		148:"ENVÍO DE DÍAS FESTIVOS",
		180:"MODIFICACIÓN DE DÍAS FESTIVOS",
		181:"LEER FIRMA ELECTRÓNICA DE LOS TOTALES INTEGRADOS POR INTERVALO DE TIEMPO (LECTURAS) CAMBIAR FECHA Y HORA",
		182:"LEER LOS PARÁMETROS DEL PUNTO DE MEDIDA",
		183:"INICIAR SESIÓN Y ENVIAR CLAVE DE ACCESO",
		184:"LEER FIRMA ELECTRÓNICA DE LOS TOTALES INTEGRADOS REPUESTOS PERIÓDICAMENTE, POR INTERVALO DE TIEMPO (INCREMENTOS DE ENERGÍA)",
		185:"LEER FECHAS Y HORAS DE CAMBIO DE HORARIO OFICIAL",
		186:"MODIFICAR FECHAS Y HORAS DE CAMBIO DE HORARIO OFICIAL",
		187:"FINALIZAR SESIÓN",
		189:"LEER BLOQUES DE TOTALES INTEGRADOS OPERACIONALES POR INTERVALO DE TIEMPO Y DIRECCIÓN",
		190:"LEER BLOQUES DE TOTALES INTEGRADOS OPERACIONALES REPUESTOS PERIÓDICAMENTE POR INTERVALO DE TIEMPO Y DIRECCIÓN",
	}
	print("      idt: "+hex(idt)+": [ASDU "+str(idt)+": "+dicc_idt[idt]+"]")

	'''byte qualificador estructura variable. Estructura: [SQ (1 bit), N (7 bits)]'''
	'''
		bit SQ:
			0 : Para cada objeto de información se indica su dirección
			1 : Se indica la dirección exclusivamente al primer objeto, siendo las direcciones del resto consecutivas.

		N (7 bits): quantitat d'objectes d'informació dins del camp ASDU
	'''
	SQ = qev & 0b10000000 == 128
	N  = qev & 0b01111111
	print("      qev: "+hex(qev)+" = "+bin(qev)+": [SQ="+str(SQ)+", N="+str(N)+" objectes d'informació]")

	'''causa de transmissio (cdt) (1 byte). Estructura: [T (1 bit), PN (1 bit), causa (6 bits)]'''
	T     = cdt & 0b10000000 == 128 # bit "test" val 1 si la trama es un test
	PN    = cdt & 0b01000000 == 64  # bit PN: "confirmacio positiva" o "negativa"
	causa = cdt & 0b00111111

	dicc_causa={
			4 :'Inicializada',
			5 :'Peticion o solicitada (request or requested)',
			6 :'Activacion',
			7 :'Confirmacion de activacion',
			8 :'Desactivacion',
			9 :'Desactivacion confirmada',
			10:'Finalizacion de la activacion',
			13:'Registro de datos solicitado no disponible',
			14:'Tipo de ASDU solicitado no disponible',
			15:'Número de registro en el ASDU enviado por CM desconocido',
			16:'Especificacion de direccion en el ASDU enviado por CM desconocida',
			17:'Objeto de informacion no disponible',
			18:'Periodo de integracion no disponible',
	}
	print("      cdt: "+hex(cdt)+": [T="+str(T)+", PN="+str(PN)+", Causa de transmissió "+str(causa)+": "+dicc_causa[causa]+"]")

	'''direccio comuna (DCO) (3 bytes). Estructura : [punt_mesura (2 bytes), registre (1 byte) ]'''
	dco_punt_mesura = dco[1] << 8 | dco[0]
	dco_registre    = dco[2]

	dicc_registre = {
			  0 :"Dirección de defecto",
			 11 :"Totales integrados con período de integración 1 (curva de carga)",
			 12 :"RESERVA. [Posible uso futuro para Totales integrados con período de integración 2(curva de carga, habitualmente cuartohoraria)].  ",
			 13 :"RESERVA. [Posible uso futuro para Totales integrados con período de integración 3(curva de carga)] ",
			 21 :"Totales integrados (valores diarios) con período de integración 1 (resumen diario)",
			 22 :"RESERVA. [Posible uso futuro para Totales integrados (valores diarios) con período de integración 2 (resumen diario)]",
			 23 :"RESERVA. [Posible uso futuro para Totales integrados (valores diarios) con período de integración 3 (resumen diario)] ",
			 52 :"Información de evento (single-point), sección 1: incidencias de arranques y tensión bajo límites ",
			 53 :"Información de evento (single-point), sección 2: incidencias de sincronización y cambio de hora ",
			 54 :"Información de evento (single-point), sección 3: incidencias de cambio de parámetros ",
			 55 :"Información de evento (single-point), sección 4: errores internos ",
			128 :"Información de evento (single-point), sección 5: incidencias de intrusismo ",
			129 :"Información de evento (single-point), sección 6: incidencias de comunicaciones ",
			130 :"Información de evento (single-point), sección 7: incidencias de clave privada ",
			131 :"Información de evento (single-point), sección 8: incidencias de Contrato I ",
			132 :"Información de evento (single-point), sección 9: incidencias de Contrato II ",
			133 :"Información de vento (single-point), sección 10: incidencias de Contrato III ",
			134 :"Información de Tarificación relativa al Contrato I",
			135 :"Información de Tarificación relativa al Contrato II",
			136 :"Información de Tarificación relativa al Contrato III",
			137 :"Información de Tarificación relativa al Contrato Latente I",
			138 :"Información de Tarificación relativa al Contrato Latente II",
			139 :"Información de Tarificación relativa al Contrato Latente III",
	}
	print("      dco (3 bytes): [punt mesura (2 bytes), direccio registre (1 byte)] = "+str(map(hex,dco)))
	print("        * punt mesura: "+str(dco_punt_mesura))
	print("        * direccio registre: "+str(dco_registre)+" = "+dicc_registre[dco_registre])
      
	'''fi'''
	print("    </iud>")

'''processa camp ASDU, dins trama variable'''
def campASDU(ASDU):
	'''
		ASDU: objecte bytearray

          6 bytes                     length var               5 bytes ò 7 bytes
		+----------------------------+---------------------+-----------------------------------+
		|  id unitat de dades (iud)  | information objects | etiqueta de temps comu (opcional) |
		+-----+-----+-----+----------+---------------------+-----------------------------------+

	'''
	n=len(ASDU)
	print("  <asdu>\n    "+str(n)+" bytes:"),
	for i in range(len(ASDU)): print hex(ASDU[i])[2:4], 
	print('')

	'''camp iud (identificador unitat de dades)'''
	iud=ASDU[0:6]
	campIUD(iud)

	'''camp objectes d'informació'''
	objsInfo=ASDU[6:n]
	campObjsInfo(objsInfo)

	'''etiqueta de temps comú'''
	# NO ESTÀ CLAR TODO

	'''fi'''
	print("  </asdu>")

def campObjsInfo(objsInfo):
	'''
		objsInfo: objecte bytearray

		estructura:

			1 byte        variable        5 ò 7 bytes
		+----------+---------------+-------------------+
		| direccio | elements info | etiqueta de temps |
		+----------+---------------+-------------------+
	'''
	n=len(objsInfo)
	print("    <objectesInfo>\n      "+str(n)+" bytes:"),

	'''mostra tots els bytes'''
	for i in range(n): print hex(objsInfo[i])[2:4],
	print('')

	'''quants objectes info hi ha? (7 bits "N" del byte QEV del camp IUD del camp ASDU)
	N=[     ASDU      ][IUD][QEV] & 7 bits    '''
	N=buf[7:len(buf)-2][0:6][ 1 ] & 0b01111111

	print("      N="+str(N)+" objectes d'informació ("+str(n/N)+" bytes cada un)")

	'''el residu entre n/N ens dona la llargada de l'etiqueta de temps comuna'''
	longitud_etiqueta = n % N
	if(longitud_etiqueta>0):
		if(longitud_etiqueta==5): print("      Amb Etiqueta comuna de 5 bytes (tipus a)")
		if(longitud_etiqueta==7): print("      Amb Etiqueta comuna de 7 bytes (tipus b)")
		if(longitud_etiqueta not in [5,7]): raise RuntimeError('Etiqueta erronia')
	else:
		print("      Sense etiqueta comuna de temps")

	'''itera els elements'''
	for i in range(N):
		inici = 0+i*(n/N) #posicio del byte inicial
		final = n/N*(i+1) #posició del byte final
		objInfo=objsInfo[inici:final] #talla l'array
		campObjInfo(objInfo)

	'''processa etiqueta si n'hi ha'''
	if(longitud_etiqueta):
		etiquetaTemps=objsInfo[n-longitud_etiqueta:n]
		campEtiquetaTemps(etiquetaTemps)

	print("    </objectesInfo>")
	'''fi'''

'''mostra un sol element d'informació'''
def campObjInfo(objInfo):
	'''
		objInfo: classe bytearray
		estructura:
			MOLT VARIABLE DEPENENT DE L'ASDU TRIAT (mirar byte idt)
			implementats:
				122
				8

	'''
	n=len(objInfo)
	print("      <objecte>")

	'''mostra tots els bytes del camp'''
	print("       "),
	for i in range(n): print hex(objInfo[i])[2:4],
	print("")

	'''mira el tipus d'ASDU'''
	'''
	idt=[    A S D      ][iud][idt] '''
	idt=buf[7:len(buf)-2][0:6][ 0 ]

	'''diccionari de direccio de registre útil per asdu 8, 122, etc'''
	dicc_direccio={
		 1:"Totales Integrados de Activa Entrante",
		 2:"Totales Integrados de Activa Saliente",
		 3:"Totales Integrados de Reactiva primer cuadrante",
		 4:"Totales Integrados de Reactiva segundo cuadrante",
		 5:"Totales Integrados de Reactiva tercer cuadrante",
		 6:"Totales Integrados de Reactiva cuarto cuadrante",
		 7:"Datos de reserva 1",
		 8:"Datos de reserva 2",
		 9:"Bloque de totales integrados genérico con datos de reserva (Punto de medida con direcciones de objeto 1 al 8) ",
		10:"Bloque de totales integrados genérico sin datos de reserva (Punto de medida con de direcciones de objeto 1 al 6) ",
		11:"Bloque de totales integrados de consumo puro sin reservas (Punto de medida con direcciones de objeto 1, 3 y 6) ",
		20:"Información de Tarificación (Totales) ",
		21:"Información de Tarificación (período tarifario 1)",
		22:"Información de Tarificación (período tarifario 2)",
		23:"Información de Tarificación (periodo tarifario 3)",
		24:"Información de Tarificación (periodo tarifario 4)",
		25:"Información de Tarificación (período tarifario 5)",
		26:"Información de Tarificación (periodo tarifario 6)",
		27:"Información de Tarificación (período tarifario 7)",
		28:"Información de Tarificación (período tarifario 8)",
		29:"Información de Tarificación (período tarifario 9)",
	}

	'''IMPLEMENTACIÓ DELS DIFERENTS TIPUS D'ASDU'''
	'''si no està implementat, dóna un runtime error'''
	if(idt==8):
		'''A8: TOTALES INTEGRADOS OPERACIONALES, 4 OCTETOS (LECTURAS DE CONTADORES ABSOLUTOS EN KWH O KVARH)'''
		'''A8 és una resposta a la petició A122'''

		'''byte 1: direccio de registre'''
		direccio=objInfo[0]
		print("        Direccio "+hex(direccio)[2:4]+": "+dicc_direccio[direccio])

		'''4 bytes següents per energia (kwh o kvarh): cal byte swap i suma'''
		nrg       = objInfo[1:5]
		nrg_valor = nrg[3] << 32 | nrg[2] << 16 | nrg[1] << 8 | nrg[0]

		print("        Energia: "+str(nrg_valor)+" (kWh o kVARh)")

		'''byte cualificador: 8 bits '''
		cualificador = objInfo[5]
		IV = cualificador & 0b10000000 == 128 # la lectura es vàlida?
		CA = cualificador & 0b01000000 == 64  # el comptador està sincronitzat?
		CY = cualificador & 0b00100000 == 32  # overflow?
		VH = cualificador & 0b00010000 == 16  # verificació horària durant el període?
		MP = cualificador & 0b00001000 == 8   # modificació de paràmetres durant el període?
		IN = cualificador & 0b00000100 == 4   # hi ha hagut intrusió durant el període?
		AL = cualificador & 0b00000010 == 2   # període incomplet per fallo d'alimentació durant el període?
		RES= cualificador & 0b00000001 == 1   # bit de reserva
		print("        byte Cualificador: "+hex(cualificador)+" : [IV="+str(IV)+",CA="+str(CA)+",CY="+str(CY)+",VH="+str(VH)+",MP="+str(MP)+",IN="+str(IN)+",AL="+str(AL)+",RES="+str(RES)+"]")
	elif(idt==122):
		'''A122: LEER TOTALES INTEGRADOS OPERACIONALES POR INTERVALO DE TIEMPO Y RANGO DE DIRECCIONES'''
		'''A122 és una petició de 4 elements: direcció inicial, direcció final, data inicial, data final'''

		'''direccio inicial'''
		direccio_inici=objInfo[0]
		print("        Direccio inici: "+str(direccio_inici)+": "+dicc_direccio[direccio_inici])

		'''direccio final'''
		direccio_final=objInfo[1]
		print("        Direcció final: "+str(direccio_final)+": "+dicc_direccio[direccio_final])

		'''etiqueta de temps inicial'''
		etiquetaInicial = objInfo[2:7]
		campEtiquetaTemps(etiquetaInicial)

		'''etiqueta de temps final'''
		etiquetaFinal = objInfo[7:12]
		campEtiquetaTemps(etiquetaFinal)
	elif(idt==134):
		'''A134: LEER INFORMACIÓN DE TARIFICACIÓN (VALORES MEMORIZADOS)'''
		'''A134 és una petició dels valors de la tarifa. la resposta és un A136'''

		'''etiqueta de temps inicial'''
		etiquetaInicial = objInfo[0:5]
		campEtiquetaTemps(etiquetaInicial)

		'''etiqueta de temps final'''
		etiquetaFinal = objInfo[5:10]
		campEtiquetaTemps(etiquetaFinal)
	elif(idt==136):
		'''A136: INFORMACIÓN DE TARIFICACIÓN (VALORES MEMORIZADOS)'''
		'''A136 és una resposta al A134'''

		'''byte 1: direccio'''
		direccio=objInfo[0]
		print("        Direcció: "+str(direccio)+": "+dicc_direccio[direccio])

		'''
			bytes 2 a 63: Informació de tarificació
		  infot (62 bytes) [VabA,VinA,CinA,VabRi,VinRi,CinRi,VabRc,VinRc,CinRc,R7,CR7,R8,CR8,VMaxA,FechaA,CMaxA,VExcA,CExcA,FechaIni,FechaFin]
		'''
		infot = objInfo[1:63]
		VabA     = infot[  0:4] #Energía absoluta Activa                     (4 bytes)
		VinA     = infot[  4:8] #Energía incremental Activa                  (4 bytes)
		CinA     = infot[    8] #Cualificador de Energía Activa              (1 bytes)
		VabRi    = infot[ 9:13] #Energía absoluta Reactiva Inductiva         (4 bytes)
		VinRi    = infot[13:17] #Energía incremental Reactiva Inductiva      (4 bytes)
		CinRi    = infot[   17] #Cualificador de Energía Reactiva Inductiva  (1 bytes)
		VabRc    = infot[18:22] #Energía absoluta Reactiva Capacitiva        (4 bytes)
		VinRc    = infot[22:26] #Energía incremental Reactiva Capacitiva     (4 bytes)
		CinRc    = infot[   26] #Cualificador de Energía Reactiva Capacitiva (1 bytes)
		R7       = infot[27:31] #Registro 7 reserva                          (4 bytes)
		CR7      = infot[   31] #Cualificador del Registro 7 de reserva      (1 bytes)
		R8       = infot[32:36] #Registro 8 reserva                          (4 bytes)
		CR8      = infot[   36] #Cualificador del Registro 8 de reserva      (1 bytes)
		VMaxA    = infot[37:41] #Máximo de las Potencias                     (4 bytes)
		FechaA   = infot[41:46] #Fecha del Máximo                            (5 bytes)
		CMaxA    = infot[   46] #Cualificador de Máximos                     (1 bytes)
		VexcA    = infot[47:51] #Excesos de las Potencias                    (4 bytes)
		CexcA    = infot[   51] #Cualificador de Excesos                     (1 bytes)
		FechaIni = infot[52:57] #Inicio del período                          (<etiqueta de tiempo tipo a> 5 bytes)
		FechaFin = infot[57:62] #Fin del período                             (<etiqueta de tiempo tipo a> 5 bytes)

		'''suma els bytes dels camps de 4 i 5 bytes'''
		VabA     =   VabA[3]<<32 |   VabA[2]<<16 |   VabA[1]<<8  |   VabA[0] 
		VinA     =   VinA[3]<<32 |   VinA[2]<<16 |   VinA[1]<<8  |   VinA[0] 
		VabRi    =  VabRi[3]<<32 |  VabRi[2]<<16 |  VabRi[1]<<8  |  VabRi[0] 
		VinRi    =  VinRi[3]<<32 |  VinRi[2]<<16 |  VinRi[1]<<8  |  VinRi[0] 
		VabRc    =  VabRc[3]<<32 |  VabRc[2]<<16 |  VabRc[1]<<8  |  VabRc[0] 
		VinRc    =  VinRc[3]<<32 |  VinRc[2]<<16 |  VinRc[1]<<8  |  VinRc[0] 
		R7       =     R7[3]<<32 |     R7[2]<<16 |     R7[1]<<8  |     R7[0] 
		R8       =     R8[3]<<32 |     R8[2]<<16 |     R8[1]<<8  |     R8[0] 
		VMaxA    =  VMaxA[3]<<32 |  VMaxA[2]<<16 |  VMaxA[1]<<8  |  VMaxA[0] 
		VexcA    =  VexcA[3]<<32 |  VexcA[2]<<16 |  VexcA[1]<<8  |  VexcA[0] 

		'''mostra'''
		print("        Energía absoluta Activa:                     "+str( VabA)+" kWh"   )
		print("        Energía incremental Activa:                  "+str( VinA)+" kWh"   )
		print("        Cualificador de Energía Activa:              "+str( CinA)          )
		print("        Energía absoluta Reactiva Inductiva:         "+str(VabRi)+" kVArh" )
		print("        Energía incremental Reactiva Inductiva:      "+str(VinRi)+" kVArh" )
		print("        Cualificador de Energía Reactiva Inductiva:  "+str(CinRi)          )
		print("        Energía absoluta Reactiva Capacitiva:        "+str(VabRc)+" kVArh" )
		print("        Energía incremental Reactiva Capacitiva:     "+str(VinRc)+" kVArh" )
		print("        Cualificador de Energía Reactiva Capacitiva: "+str(CinRc)          )
		print("        Registro 7 reserva:                          "+str(   R7)          )
		print("        Cualificador del Registro 7 de reserva:      "+str(  CR7)          )
		print("        Registro 8 reserva:                          "+str(   R8)          )
		print("        Cualificador del Registro 8 de reserva:      "+str(  CR8)          )
		print("        Máximo de las Potencias:                     "+str(VMaxA)+" kW"    )
		print("        Fecha del Máximo:                            "); campEtiquetaTemps(FechaA)
		print("        Cualificador de Máximos:                     "+str(CMaxA)          )
		print("        Excesos de las Potencias:                    "+str(VexcA)+" kW"    )
		print("        Cualificador de Excesos:                     "+str(CexcA)          )
		print("        Inicio del período:                          "); campEtiquetaTemps(FechaIni)
		print("        Fin del período:                             "); campEtiquetaTemps(FechaFin)
	elif(idt==183):
		'''A183: INICIAR SESIÓN Y ENVIAR CLAVE DE ACCESO'''
		'''A183 és una petició d'inici de sessió'''
		clau = objInfo[0:4]

		'''suma els 4 bytes de la clau d'accés'''
		clau = clau[3]<<32 | clau[2]<<16 | clau[1]<<8 | clau[0]
		print("        Clau d'accés: "+str(clau))
	else:
		raise RuntimeError("[!] ERROR: ASDU "+str(idt)+" ENCARA NO IMPLEMENTAT")

	'''fi'''
	print("      </objecte>")

'''processa una sola etiqueta de temps'''
def campEtiquetaTemps(etiqueta):
	'''
		etiqueta: classe bytearray

		l'etiqueta de temps conté una data

		pot ser: 
			* tipus a (5 bytes) 
			* tipus b (7 bytes)
	'''
	n=len(etiqueta)

	'''comprova el tipus d'etiqueta'''
	if(n==5):   tipus="a"
	elif(n==7): tipus="b"
	else: raise RuntimeError("Etiqueta de temps desconeguda")

	if tipus=="b":
		print("          Etiqueta Tipus b encara no implementada")
		return

	'''mostra l'etiqueta'''
	print("        <etiqueta> tipus "+tipus+" ("+str(n)+" bytes):"),
	for i in range(n): print hex(etiqueta[i])[2:4],
	print('')

	'''
		Estructura dels 5 bytes == 40 bits

			 1-6     7     8   9-13   14-15   16    17-21     22-24     25-28   29-30   31-32   33-39    40
		+-------+-----+----+------+-------+----+--------+-----------+-------+-------+-------+-------+------+
    | minut | TIS | IV | hora |  RES1 | SU | diames | diasemana |  mes  |  ETI  |  PTI  |  year | RES2 |
    +-------+-----+----+------+-------+----+--------+-----------+-------+-------+-------+-------+------+
	'''
	minut     = etiqueta[0] & 0b11111100 >> 2 
	TIS       = etiqueta[0] & 0b00000010 == 2
	IV        = etiqueta[0] & 0b00000001 
	hora      = etiqueta[1] & 0b11111000 >> 3
	RES1      = etiqueta[1] & 0b00000110 >> 1
	SU        = etiqueta[1] & 0b00000001
	diames    = etiqueta[2] & 0b11111000 >> 3
	diasemana = etiqueta[2] & 0b00000111 
	mes       = etiqueta[3] & 0b11110000 >> 4
	ETI       = etiqueta[3] & 0b00001100 >> 2
	PTI       = etiqueta[3] & 0b00000011
	year      = etiqueta[4] & 0b11111110 >> 1
	RES2      = etiqueta[4] & 0b00000001

	'''completa l'any'''
	year+=2000

	'''detall estètic: posa un zero davant el número de: diames, mes, hora i minuts més petits de 10'''
	if(diames<10): diames="0"+str(diames)
	if(mes   <10): mes="0"+str(mes)
	if(hora  <10): hora="0"+str(hora)
	if(minut <10): minut="0"+str(minut)

	'''fi'''
	print("          Data: "+str(diames)+"/"+str(mes)+"/"+str(year)+" "+str(hora)+":"+str(minut))
	print("        </etiqueta>")

#==#==#==#==#==#==#==#==#==#==#==#
#                                #
#      T R A M E S  T E S T      #
#                                #
#==#==#==#==#==#==#==#==#==#==#==#
'''trames fixes: ok'''
#pregunta
#processa('\x10\x49\x01\x00\x4a\x16')
#resposta
#processa('\x10\x0b\x01\x00\x0c\x16') 

'''trames variables, 2 tipus: integrados i lecturas'''

'''integrados totales'''
#pregunta: ASDU 122
#processa('\x68\x15\x15\x68\x73\x58\x1B\x7A\x01\x06\x01\x00\x0B\x01\x08\x00\x0B\x07\x02\x0A\x00\x11\x0A\x02\x0A\xC1\x16')
#resposta: ASDU 8
#processa('\x68\x3E\x3E\x68\x08\x58\x1B\x08\x08\x05\x01\x00\x0B\x01\x18\x01\x00\x00\x00\x02\x6E\x1F\x03\x00\x00\x03\x04\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x05\xCC\xBE\x00\x00\x00\x06\x98\x0D\x00\x00\x00\x07\x00\x00\x00\x00\x80\x08\x00\x00\x00\x00\x80\x00\x81\xB2\x09\x09\xE1\x16')

'''lecturas de cierre '''
#pregunta: ASDU 134
#processa('\x68\x13\x13\x68\x73\x58\x1B\x86\x01\x06\x01\x00\x88\x00\x00\x01\x0A\x09\x00\x00\x01\x02\x0A\x1D\x16')
#resposta: ASDU 136
#processa('\x68\x48\x48\x68\x08\x58\x1B\x88\x01\x05\x01\x00\x88\x14\x61\x71\x00\x00\xE4\x25\x00\x00\x00\x0B\x47\x00\x00\x88\x09\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x54\x00\x00\x00\x00\x0E\xBA\x0C\x08\x00\x00\x00\x00\x00\x80\x00\x00\x21\x0C\x08\x00\x00\x81\x01\x09\xD4\x16')

'''peticio de link i enviament de contrasenya'''
#pregunta ASDU 183
#processa("\x68\x0D\x0D\x68\x73\x58\x1B\xB7\x01\x06\x01\x00\x00\x4E\x61\xBC\x00\x10\x16")