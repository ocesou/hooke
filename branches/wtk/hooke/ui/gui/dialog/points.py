# Copyright

import wx


def measure_N_points(hooke_frame, N, message='', block=0):
    '''
    General helper function for N-points measurements
    By default, measurements are done on the retraction
    '''
    if message:
        dialog = wx.MessageDialog(None, message, 'Info', wx.OK)
        dialog.ShowModal()

    figure = self.GetActiveFigure()

    xvector = self.displayed_plot.curves[block].x
    yvector = self.displayed_plot.curves[block].y

    clicked_points = figure.ginput(N, timeout=-1, show_clicks=True)

    points = []
    for clicked_point in clicked_points:
        point = lib.clickedpoint.ClickedPoint()
        point.absolute_coords = clicked_point[0], clicked_point[1]
        point.dest = 0
        #TODO: make this optional?
        #so far, the clicked point is taken, not the corresponding data point
        point.find_graph_coords(xvector, yvector)
        point.is_line_edge = True
        point.is_marker = True
        points.append(point)
    return points
