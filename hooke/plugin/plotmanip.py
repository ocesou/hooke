
class Plotmanip (object):
#-----PLOT MANIPULATORS
    def plotmanip_median(self, plot, current, customvalue=None):
        '''
        does the median of the y values of a plot
        '''
        if customvalue:
            median_filter=customvalue
        else:
            median_filter=self.config['medfilt']

        if median_filter==0:
            return plot

        if float(median_filter)/2 == int(median_filter)/2:
            median_filter+=1

        nplots=len(plot.vectors)
        c=0
        while c<nplots:
            plot.vectors[c][1]=scipy.signal.medfilt(plot.vectors[c][1],median_filter)
            c+=1

        return plot


    def plotmanip_correct(self, plot, current, customvalue=None):
        '''
        does the correction for the deflection for a force spectroscopy curve.
        Assumes that:
        - the current plot has a deflection() method that returns a vector of values
        - the deflection() vector is as long as the X of extension + the X of retraction
        - plot.vectors[0][0] is the X of extension curve
        - plot.vectors[1][0] is the X of retraction curve

        FIXME: both this method and the picoforce driver have to be updated, deflection() must return
        a more senseful data structure!
        '''
        #use only for force spectroscopy experiments!
        if current.curve.experiment != 'smfs':
            return plot

        if customvalue != None:
            execute_me=customvalue
        else:
            execute_me=self.config['correct']
        if not execute_me:
            return plot

        defl_ext,defl_ret=current.curve.deflection()
        #halflen=len(deflall)/2

        plot.vectors[0][0]=[(zpoint-deflpoint) for zpoint,deflpoint in zip(plot.vectors[0][0],defl_ext)]
        plot.vectors[1][0]=[(zpoint-deflpoint) for zpoint,deflpoint in zip(plot.vectors[1][0],defl_ret)]

        return plot


    def plotmanip_centerzero(self, plot, current, customvalue=None):
        '''
        Centers the force curve so the median (the free level) corresponds to 0 N
        Assumes that:
        - plot.vectors[0][1] is the Y of extension curve
        - plot.vectors[1][1] is the Y of retraction curve
        
       
        '''
        #use only for force spectroscopy experiments!
        if current.curve.experiment != 'smfs':
            return plot
    
        if customvalue != None:
            execute_me=customvalue
        else:
            execute_me=self.config['centerzero']
        if not execute_me:
            return plot
     
        
	
	#levelapp=float(np.median(plot.vectors[0][1]))
	levelret=float(np.median(plot.vectors[1][1][-300:-1]))

	level=levelret	

	approach=[i-level for i in plot.vectors[0][1]]
	retract=[i-level for i in plot.vectors[1][1]]
	
	plot.vectors[0][1]=approach	
	plot.vectors[1][1]=retract	
        return plot
