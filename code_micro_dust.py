from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file,client,tools

import serial
import time
import pigpio
import struct
import datetime

SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
store = file.Storage('token.json')
creds = store.get()
if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credential.json', SCOPES)
        creds = tools.run_flow(flow, store)
        service = build('sheets', 'v4', http=creds.authorize(Http()))
# Call the Sheets API
SPREADSHEET_ID = '1e47cCd3v4qKT69ICvlubE5y185hLQy5RklnG0RAPLME
                  1e47cCd3v4qKT69ICvIubE5y185hLQy5RklnG0RAPLME'
RANGE_NAME = 'Sheet3!A2'

class PMSA003: 
	#constants
	PMS_FRAME_LENGTH = 0
	PMS_PM1_0 = 1
	PMS_PM2_5 = 2
	PMS_PM10_0 = 3
	PMS_PM1_0_ATM = 4
	PMS_PM2_5_ATM = 5
	PMS_PM10_0_ATM = 6
	PMS_PCNT_0_3 = 7
	PMS_PCNT_0_5 = 8
	PMS_PCNT_1_0 = 9
	PMS_PCNT_2_5 = 10
	PMS_PCNT_5_0 = 11
	PMS_PCNT_10_0 = 12
	PMS_VERSION = 13
	PMS_ERROR = 14
	PMS_CHECKSUM = 15
	PMS_WAIT_TIME = 30 #time to wait when sensor exits sleep mode
	
	def __init__(self, resetPin = 17, setPin = 18): 
		#defining GPIO for RESET line and SET line
		self.resetPin = resetPin
		self.setPin = setPin
		#opening serial port
		self.device = serial.Serial(port= '/dev/ttyAMA0',
					baudrate= 9600,
					stopbits= serial.STOPBITS_ONE,
					parity= serial.PARITY_NONE,
					bytesize= serial.EIGHTBITS,
					timeout= 5)
		if not self.device.isOpen(): raise IOError("Unable to open serial") 
		#open connection to pigpio
		self.pi = pigpio.pi()
		if not self.pi.connected: raise IOError("Unable to connect to PiGPIOd")
 
	def getLastReading(self):
		#get last sensor reading
		#flushing input buffer if it's bigger than one reading because i want last reading
		if self.device.in_waiting > 32:
			self.device.reset_input_buffer()

		readEnd = False
		while readEnd is not True:
			while True:
				#checking start frame: 0x42 and 0x4D
				firstByte = self.device.read(1)
				if len(firstByte) < 1 or ord(firstByte) != 0x42: break
				secondByte = self.device.read(1)
				if len(secondByte) < 1 or ord(secondByte) != 0x4D: break

				#reading all the rest!
				readBuffer = self.device.read(30)
				if len(readBuffer) < 30: break

				#decoding data
				data = struct.unpack('!HHHHHHHHHHHHHBBH', readBuffer)

				#checking checksum
				checksum = 0x42 + 0x4D
				for c in readBuffer[0:28]: checksum += c
				if checksum != data[self.PMS_CHECKSUM]:
					print("Incorrect check code: received : {:04x}, calculated : {:04x}".format(data[self.PMS_CHECKSUM],checksum))
				
				#Dust Data
					
				dustValues = [[data[self.PMS_PM10_0_ATM]]]
				contents ={'values': dustValues}
				result = service.spreadsheets().values().update(spreadsheetId = SPREADSHEET_ID,range = RANGE_NAME,valueInputOption = 'USER_ENTERED', body = contents).execute()
				print('{0} cells updated.'.format(result.get('updateCells')));


				super_micro_dust = data[self.PMS_PM2_5_ATM]
				
				print(datetime.datetime.now())
				print(dust)

				readEnd = True
				print("done")
				break
			
	def setSleepMode (self, sleepMode):
		#set sensor sleep mode - SETPIN
		if sleepMode is True:
			self.pi.write(self.setPin, 0)
		else:
			self.pi.write(self.setPin, 1)
			#need to wait some time to get proper readings
			time.sleep(self.PMS_WAIT_TIME)
	
	def setStandbyMode (self, standbyMode):
		#set sensor standby mode - SERIAL
		#command is built as: 0x42 0x4d 0xe4 0x00 0x00/01 checksum
		#standbyMode TRUE sets standby
		if standbyMode is True:
			checksum = 0x42+0x4D+0xE4+0x00+0x00
			serCmd = struct.pack('!BBBBBH',0x42,0x4D,0xE4,0x00,0x00,checksum)
			self.device.write(serCmd)
			self.device.reset_input_buffer()
			#checking response: 42 4D 00 04 E4 00 chckH chckL
			response = self.device.read(8)
			if len(response) < 8: print("Response error")
			expected = bytes([0x42,0x4D,0x00,0x04,0xE4,0x00,0x01,0x77])
			if(response != expected):
				print("Wrong response received: {} - expected {}".format(response,expected))
			else:
				print("Standby set")
		else:
			checksum = 0x42+0x4D+0xE4+0x00+0x01
			serCmd = struct.pack('!BBBBBH',0x42,0x4D,0xE4,0x00,0x01,checksum)
			self.device.write(serCmd)
			self.device.reset_input_buffer()
			#no answer expected
			#need to wait some time to get proper readings
			time.sleep(self.PMS_WAIT_TIME)
			print("Standby removed")
		
	def setActiveMode (self, active):
		#set sensor state - SERIAL
		#command is built as: 0x42 0x4d 0xe1 0x00 0x00/01 checksum
		#active TRUE sets active mode
		if active is True:
			checksum = 0x42+0x4D+0xE1+0x00+0x01
			serCmd = struct.pack('!BBBBBH',0x42,0x4D,0xE1,0x00,0x01,checksum)
			self.device.write(serCmd)
			self.device.reset_input_buffer()
			#no answer expected
			print("Active mode set")
		else:
			checksum = 0x42+0x4D+0xE1+0x00+0x00
			serCmd = struct.pack('!BBBBBH',0x42,0x4D,0xE1,0x00,0x00,checksum)
			self.device.write(serCmd)
			self.device.reset_input_buffer()
			#checking response: 42 4D 00 04 E1 00 1 74
			response = self.device.read(8)
			if len(response) < 8: print("Response error")
			expected = bytes([0x42,0x4D,0x00,0x04,0xE1,0x00,0x01,0x74])
			if(response != expected):
				print("Wrong response received: {} - expected {}".format(response,expected))
			else:
				print("Passive mode set")
			#in passive mode i expect to have single readings, so i'm trashing all the input buffer
			self.device.reset_input_buffer()
	
	def getSingleReading(self):
		#trigger single reading on passive mode
		checksum = 0x42+0x4D+0xe2+0x00+0x00
		serCmd = struct.pack('!BBBBBH',0x42,0x4D,0xE2,0x00,0x00,checksum)
		self.device.write(serCmd)
		self.getLastReading()
	
	def reset (self):
		#reset sensor - RESETPIN
		self.pi.write(self.resetPin, 0)
		time.sleep(0.5)
		self.pi.write(self.resetPin, 1)
	
	def close(self): 
		''' Close the serial port.'''
		self.device.close()
		self.pi.stop()

if __name__ == "__main__":
    sensor = PMSA003()
    print("Setting active")
    sensor.setActiveMode(True)	
    #print("Setting standby")
    #sensor.setStandbyMode(True)
    #time.sleep(1)
    #print("Removing standby")
    #sensor.setStandbyMode(False)
    #time.sleep(1)
    for i in range(100):
        sensor.getLastReading()
        time.sleep(1)
    #sensor.getSingleReading()
    #time.sleep(1)
    #sensor.getSingleReading()
	
    sensor.close()
