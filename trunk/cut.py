# -*- coding: utf-8 -*-
class cutCommands:

    def _plug_init(self):
        self.cut_basecurrent=None
        self.cut_basepoints=None




    def do_cut(self,args):
        '''
CUT
        (cut.py)
        Cut the selected signal between two points.
        With the first parameter you have to select the signal (for FS for example
        you can select with "0" the approacing curve and 1 for the retracting
	curve. This depend also on how many set of data you have on the graph).
        With the second parameter you select the output name file for the selection.
	The data is arranged in two simple column without a header, the first column
	is the "x" data and the second the "y".
        -----------------
        Syntax: distance "whatset" "namefile"
        '''
        if len(args)==0:
		print "This command need the number of the graph that you want save and a name for the output file."
		return
	
	a=args.split()
	
	
	whatset=int(a[0])
	outfile=a[1]
	plot=self._get_displayed_plot()

        print 'Select two points'
        points=self._measure_N_points(N=2, whatset=whatset)
	minbound=min(points[0].index, points[1].index)
	maxbound=max(points[0].index, points[1].index)
        boundpoints=[minbound, maxbound]
	yarr=plot.vectors[whatset][1][boundpoints[0]:boundpoints[1]]
	xarr=plot.vectors[whatset][0][boundpoints[0]:boundpoints[1]]

	f=open(outfile,'w+')
	for i in range(len(yarr)):
		f.write(str(xarr[i])+";"+str(yarr[i])+"\n")
        f.close()



