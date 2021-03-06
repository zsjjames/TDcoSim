import os
import copy
import json
import pdb
from itertools import product

import pandas as pd
import matplotlib.pyplot as plt
import psspy
import dyntools

from tdcosim.data_analytics import DataAnalytics
from utils import PrintException


class PostProcess(DataAnalytics):
	def __init__(self):
		super(DataAnalytics,self).__init__()
		self.baseDir=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
		self.outDir=self.baseDir+os.path.sep+'data'+os.path.sep+'out'
		self.metadata={'scenarioid':'','tag':'','config':{}}
		self.search_scope('','')
		return None

#=======================================================================================================================
	def add_metadata(self,scenarioid,tag,config):
		try:
			self.metadata['scenarioid']=scenarioid
			self.metadata['tag']=tag
			self.metadata['config']=config
		except:
			PrintException()

#=======================================================================================================================
	def load_outfile(self,fpath):
		try:
			# convert to df
			dfOld=self._dict2df_outfile(fpath)

			# reformat
			df=pd.DataFrame(columns=['time','scenarioid','tag','busid','property','value'])
			df.time=dfOld.t
			df.scenarioid=[self.metadata['scenarioid']]*len(dfOld.t)
			df.tag=[self.metadata['tag']]*len(dfOld.t)
			df.busid=dfOld.tnodeid
			df.property=dfOld.property
			df.value=dfOld.value

			# change property names
			df.property=df.property.map(self.__mapper)

			return df
		except:
			PrintException()

#=======================================================================================================================
	def __mapper(self,x,mapio={'POWR':'pinj','VARS':'qinj','PLOD':'pd','QLOD':'qd',
	'SPD':'omega','VOLT':'vmag','PMEC':'pmech','ANGL':'delta'}):
		try:
			if x in mapio:
				x=mapio[x]
			return x
		except:
			PrintException()

#=======================================================================================================================
	def show_plot(self,df,propertyid,ylabel='',title=''):
		try:
			df=df[df.property==propertyid]
			df=df.sort_values(by='time',ascending=True)
			legend=[]
			for thisBusid in set(df.busid):
				thisDF=df[df.busid==thisBusid]
				plt.plot(thisDF.time,thisDF.value)
				legend.append(thisBusid)

			plt.xlabel('Time (s)')
			plt.ylabel(ylabel)
			plt.title(title)
			plt.legend(legend)
			plt.show()
		except Exception as e:
			logging.error(e)

#=======================================================================================================================
	def save(self,df):
		try:
			for thisScenario,thisTag in product(*(set(df.scenarioid),set(df.tag))):
				thisDF=df[(df.scenarioid==thisScenario)&(df.tag==thisTag)]
				if not thisDF.empty:
					dirPath=self.outDir+os.path.sep+'{}_{}'.format(thisScenario,thisTag)
					if not os.path.exists(dirPath):
						os.mkdir(dirPath)
					thisDF.to_pickle(open(dirPath+os.path.sep+'{}_{}_df.pkl'.format(thisScenario,thisTag),'wb'),
					compression=None)
					json.dump(self.metadata['config'],open(dirPath+os.path.sep+'{}_{}_config.json'.format(\
					thisScenario,thisTag),'w'),indent=3)
		except:
			PrintException()

#=======================================================================================================================
	def search_scope(self,scenarioid,tag):
		try:
			if isinstance(scenarioid,str):
				scenarioid=[scenarioid]
			if isinstance(tag,str):
				tag=[tag]

			self.index={'info':{},'path':[]}
			for thisScenario,thisTag in zip(scenarioid,tag):
				if thisScenario not in self.index['info']:
					self.index['info'][thisScenario]={}
				self.index['info'][thisScenario][thisTag]={}
				dirPath=self.outDir+os.path.sep+'{}_{}'.format(thisScenario,thisTag)
				self.index['path'].append(dirPath+os.path.sep+'{}_{}_df.pkl'.format(thisScenario,thisTag))
		except:
			PrintException()

#=======================================================================================================================
	def filter_node(self,busid,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()

			if isinstance(busid,str) or isinstance(busid,int):
				busid=[busid]

			filteredDF=pd.DataFrame(columns=df.columns)
			for thisNode in busid:
				filteredDF=filteredDF.append(df[df.busid==thisNode],ignore_index=True)

			filteredDF.index=range(len(filteredDF))
			return filteredDF
		except:
			PrintException()

#===================================================================================================
	def filter_time(self,fromTime,toTime,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()
			df=df[(df.value>=fromTime)&(df.value<=toTime)]
			return df
		except:
			PrintException()

#===================================================================================================
	def filter_property(self,propertyid,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()

			if isinstance(propertyid,str) or isinstance(propertyid,int):
				propertyid=[propertyid]

			filteredDF=pd.DataFrame(columns=df.columns)
			for thisproperty in propertyid:
				filteredDF=filteredDF.append(df[df.property==thisproperty],ignore_index=True)

			filteredDF.index=range(len(filteredDF))
			return filteredDF
		except:
			PrintException()

#===================================================================================================
	def filter_value(self,fromValue,toValue,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()
			df=df[(df.value>=fromValue)&(df.value<=toValue)]
			return df
		except:
			PrintException()

#===================================================================================================
	def filter_violations(self,lowerLimit,upperLimit,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()
			df=df[(df.value<=lowerLimit)|(df.value>=upperLimit)]
			return df
		except:
			PrintException()
            
#===================================================================================================
	def get_df(self):
		try:
			df=pd.DataFrame(columns=['time','scenarioid','tag','busid','property','value'])
			for thisDFPath in self.index['path']:
				df=df.append(pd.read_pickle(open(thisDFPath,'rb'),compression=None))
			return df
		except:
			PrintException()

#===================================================================================================
	def show_voltage_violations(self,vmin,vmax,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()

			VFilt=self.filter_value(vmin,vmax,df[df.property=='vmag'])

			legend=[]
			for thisBusId in set(VFilt.busid):
				for thisScenario in set(VFilt.scenarioid):
					for thisTag in set(VFilt.tag):
						thisDf=df[(df.busid==thisBusId)&(df.property=='vmag')&\
						(df.scenarioid==thisScenario)&(df.tag==thisTag)]
						if not thisDf.empty:
							plt.plot(thisDf.time,thisDf.value)
							legend.append('{}:{}:{}'.format(thisBusId,thisScenario,thisTag))
			plt.legend(legend)
			plt.title('Voltage Violations\nViolation:Vmag >={} and <={} pu'.format(vmin,vmax))
			plt.show()
		except:
			PrintException()

#===================================================================================================
	def show_voltage_violations_der(self,vmin,vmax,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()
			time_values = self.get_time_values(df)
			print('Minimum voltage:{:.2f},Maximum voltage:{:.2f}'.format(df[df.property=='vmag'].value.min(),df[df.property=='vmag'].value.max()))
			#VFilt=self.filter_value(vmin,vmax,df[(df.property=='vmag')& (df.phase=='a')])
			VFilt=self.filter_violations(vmin,vmax,df[(df.property=='vmag')& (df.phase=='a')])

			print('Original distribution nodes:{},Filtered distribution nodes:{}'.format(list(set(df.dnodeid)),list(set(VFilt.dnodeid))))
			print('Original samples:{},Filtered samples:{}'.format(len(df),len(VFilt)))
			legend=[];thisDf_list=[]
			plt.figure(figsize=(10,10))
			for thisBusId in set(VFilt.busid):
				for thisScenario in set(VFilt.scenarioid):
					for thisTag in set(VFilt.tag):
						for thisDnodeId in set(VFilt.dnodeid):
							thisDf=VFilt[(VFilt.busid==thisBusId)&(VFilt.property=='vmag')&\
							(VFilt.scenarioid==thisScenario)&(VFilt.tag==thisTag)&(VFilt.dnodeid==thisDnodeId)]
							if not thisDf.empty:
								thisDf_list.append(thisDf)
								plt.scatter(thisDf.time,thisDf.value,s=10.0)								
								legend.append('{}-{}-a:{}:{}'.format(thisBusId,thisDnodeId,thisScenario,thisTag,thisTag))
			
			
			plt.scatter(time_values,[vmin]*len(time_values),s=10.0,marker=".")
			plt.scatter(time_values,[vmax]*len(time_values),s=10.0,marker=".")
			legend.append('Vmin--{}'.format(vmin))
			legend.append('Vmax--{}'.format(vmax))
			
			plt.ylabel('Voltage (p.u.)',weight = "bold", fontsize=10)
			plt.xlabel('Time (s)',weight = "bold", fontsize=10)
			plt.legend(legend)
			plt.title('Voltage Violations\nViolation:Vmag <={} and >={} pu'.format(vmin,vmax))
			plt.show()
			return thisDf_list
            
		except:
			PrintException()

#===================================================================================================
	def show_voltage_recovery(self,vmin,vmax,maxRecoveryTime,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()

			VFilt=self.filter_value(vmin,vmax,df[df.property=='vmag'])

			legend=[]
			for thisBusId in set(VFilt.busid):
				for thisScenario in set(VFilt.scenarioid):
					for thisTag in set(VFilt.tag):
						thisDf=df[(df.busid==thisBusId)&(df.property=='vmag')&\
						(df.scenarioid==thisScenario)&(df.tag==thisTag)]
						thisDf=thisDf.sort_values(by='time')
						startFlag=False; startTime=0
						for thisTime,thisVal in zip(thisDf.time,thisDf.value):
							if thisVal>=vmin and thisVal<=vmax and not startFlag:
								startFlag=True
								startTime=thisTime
							elif thisVal>=vmin and thisVal<=vmax and startFlag and thisTime-startTime>=maxRecoveryTime:
								startFlag=False
								legend.append('{}:{}:{}'.format(thisBusId,thisScenario,thisTag))
								break

			if legend:
				for entry in legend:
					thisBusId=entry.split(':')[0]
					thisDf=df[(df.busid==thisBusId)&(df.property=='vmag')&\
					(df.scenarioid==thisScenario)&(df.tag==thisTag)]
					if not thisDf.empty:
						plt.plot(thisDf.time,thisDf.value)

				plt.legend(legend)
				plt.title('Voltage Violations\nViolation:Vmag >={} and <={} pu for time>={}'.format(vmin,vmax,maxRecoveryTime))
				plt.show()
		except:
			PrintException()

#===================================================================================================
	def show_voltage_recovery_der(self,vmin,vmax,maxRecoveryTime,df=None):
		try:
			if not isinstance(df,pd.DataFrame):
				df=self.get_df()
			
			time_values = self.get_time_values(df)
			VFilt=self.filter_value(vmin,vmax,df[df.property=='vmag'])

			legend=[]
			violation_nodes = []
			for thisBusId in set(VFilt.busid):
				for thisDnodeId in set(VFilt.dnodeid):
					for thisScenario in set(VFilt.scenarioid):
						for thisTag in set(VFilt.tag):
							thisDf=df[(df.busid==thisBusId)&(df.dnodeid==thisDnodeId)&(df.phase=='a')&(df.property=='vmag')&(df.scenarioid==thisScenario)&(df.tag==thisTag)]
							thisDf=thisDf.sort_values(by='time')
							#print(thisBusId,thisDnodeId,thisScenario,thisDf.shape)
							startFlag=False; startTime=0
							for thisTime,thisVal in zip(thisDf.time,thisDf.value):
								if (thisVal<=vmin or thisVal>=vmax) and not startFlag:
									startFlag=True
									startTime=thisTime
									#print('Timer started at {} s for node {} at {} V'.format(thisTime,thisDnodeId,thisVal))
								if thisVal>vmin and thisVal<vmax and startFlag:
									startFlag=False
									startTime=thisTime
									#print('Timer reset at {} s for node {} at {} V'.format(thisTime,thisDnodeId,thisVal))
								if (thisVal<=vmin or thisVal>=vmax) and startFlag:
									if thisTime-startTime>=maxRecoveryTime:
										#startFlag=False
										print('Timer breached at {:.2f} s after {:.2f} s for node {} at {:.2f} V'.format(thisTime,thisTime-startTime,thisDnodeId,thisVal))
										legend.append('{}:{}:{}:{}'.format(thisBusId,thisDnodeId,thisScenario,thisTag))
										violation_nodes.append(thisDnodeId)
										break
			thisDf_list = []
			print('{} nodes had recovery time > {} s:{}'.format(len(violation_nodes),maxRecoveryTime,violation_nodes))
			if legend:
				plt.figure(figsize=(10,10))
				for entry in legend:
					thisBusId=entry.split(':')[0]
					thisDnodeId=entry.split(':')[1]
					thisScenario=entry.split(':')[2]
					thisTag=entry.split(':')[3]
					
					thisDf=df[(df.busid==thisBusId)&(df.dnodeid==thisDnodeId)&(df.phase=='a')&(df.property=='vmag')&(df.scenarioid==thisScenario)&(df.tag==thisTag)]
					
					if not thisDf.empty:
						thisDf_list.append(thisDf)
						plt.plot(thisDf.time,thisDf.value)
				
				plt.scatter(time_values,[vmin]*len(time_values),s=10.0,marker=".")
				plt.scatter(time_values,[vmax]*len(time_values),s=10.0,marker=".")
				legend.append('Vmin--{}'.format(vmin))
				legend.append('Vmax--{}'.format(vmax))
				plt.ylabel('Voltage (p.u.)',weight = "bold", fontsize=10)
				plt.xlabel('Time (s)',weight = "bold", fontsize=10)
				plt.legend(legend)
				plt.title('Voltage Violations\nViolation:Vmag <={} or >={} pu for time>={}'.format(vmin,vmax,maxRecoveryTime))
				plt.show()
			return thisDf_list
		except:
			PrintException()


