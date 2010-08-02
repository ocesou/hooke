# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

#PLOT INTERACTION COMMANDS
#-------------------------------
    def help_plot(self):
        print '''
PLOT
Plots the current force curve
-------
Syntax: plot
        '''
    def do_plot(self,args):
        if self.current.identify(self.drivers) == False:
            return
        self.plots=self.current.curve.default_plots()
        try:
            self.plots=self.current.curve.default_plots()
        except Exception, e:
            print 'Unexpected error occurred in do_plot().'
            print e
            return

        #apply the plotmanip functions eventually present
        nplots=len(self.plots)
        c=0
        while c<nplots:
            for function in self.plotmanip: #FIXME: something strange happens about self.plotmanip[0]
                self.plots[c]=function(self.plots[c], self.current)

            self.plots[c].xaxes=self.config['xaxes'] #FIXME: in the future, xaxes and yaxes should be set per-plot
            self.plots[c].yaxes=self.config['yaxes']

            c+=1

        self._send_plot(self.plots)

    def _delta(self, set=1):
        '''
        calculates the difference between two clicked points
        '''
        print 'Click two points'
        points=self._measure_N_points(N=2, whatset=set)
        dx=abs(points[0].graph_coords[0]-points[1].graph_coords[0])
        dy=abs(points[0].graph_coords[1]-points[1].graph_coords[1])
        unitx=self.plots[points[0].dest].units[0]
        unity=self.plots[points[0].dest].units[1]
        return dx,unitx,dy,unity

    def do_delta(self,args):
        '''
        DELTA

        Measures the delta X and delta Y between two points.
        ----
        Syntax: delta
        '''
        dx,unitx,dy,unity=self._delta()
        print str(dx)+' '+unitx
        print str(dy)+' '+unity

    def _point(self, set=1):
        '''calculates the coordinates of a single clicked point'''

        print 'Click one point'
        point=self._measure_N_points(N=1, whatset=set)

        x=point[0].graph_coords[0]
        y=point[0].graph_coords[1]
        unitx=self.plots[point[0].dest].units[0]
        unity=self.plots[point[0].dest].units[1]
        return x,unitx,y,unity

    def do_point(self,args):
        '''
        POINT

        Returns the coordinates of a point on the graph.
        ----
        Syntax: point
        '''
        x,unitx,y,unity=self._point()
        print str(x)+' '+unitx
        print str(y)+' '+unity
        to_dump='point '+self.current.path+' '+str(x)+' '+unitx+', '+str(y)+' '+unity
        self.outlet.push(to_dump)


    def do_close(self,args=None):
        '''
        CLOSE
        Closes one of the two plots. If no arguments are given, the bottom plot is closed.
        ------
        Syntax: close [top,bottom]
        '''
        if args=='top':
            to_close=0
        elif args=='bottom':
            to_close=1
        else:
            to_close=1

        close_plot=self.list_of_events['close_plot']
        wx.PostEvent(self.frame, close_plot(to_close=to_close))

    def do_show(self,args=None):
        '''
        SHOW
        Shows both plots.
        '''
        show_plots=self.list_of_events['show_plots']
        wx.PostEvent(self.frame, show_plots())

#HELPER FUNCTIONS
#Everything sending an event should be here
    def _measure_N_points(self, N, whatset=1):
        '''
        general helper function for N-points measures
        '''
        wx.PostEvent(self.frame,self.list_of_events['measure_points'](num_of_points=N, set=whatset))
        while 1:
            try:
                points=self.frame.events_from_gui.get()
                break
            except Empty:
                pass
        return points

    def _get_displayed_plot(self,dest=0):
        '''
        returns the currently displayed plot.
        '''
        wx.PostEvent(self.frame, self.list_of_events['get_displayed_plot'](dest=dest))
        while 1:
            try:
                displayed_plot=self.events_from_gui.get()
            except Empty:
                pass
            if displayed_plot:
                break
        return displayed_plot

    def _send_plot(self,plots):
        '''
        sends a plot to the GUI
        '''
        wx.PostEvent(self.frame, self.list_of_events['plot_graph'](plots=plots))
        return

    def _find_plotmanip(self, name):
        '''
        returns a plot manipulator function from its name
        '''
        return self.plotmanip[self.config['plotmanips'].index(name)]

    def _clickize(self, xvector, yvector, index):
        '''
        returns a ClickedPoint() object from an index and vectors of x, y coordinates
        '''
        point=ClickedPoint()
        point.index=index
        point.absolute_coords=xvector[index],yvector[index]
        point.find_graph_coords(xvector,yvector)
        return point
