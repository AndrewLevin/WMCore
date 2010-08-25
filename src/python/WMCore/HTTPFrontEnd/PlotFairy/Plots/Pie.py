from Plot import Plot
from Mixins import *
from Validators import *

class Pie(FigureMixin,TitleMixin,FigAxesMixin,StyleMixin,LabelledSeriesMixin,WatermarkMixin):
    '''
    A simple pie chart.
    '''
    __metaclass__=Plot
    def __init__(self):
        self.validators = [ElementBase('shadow',bool,default=True,doc_user="Draw a drop-shadow."),
                           ElementBase('percentage',bool,default=True,doc_user="Draw a percentage inside each slice.")]
        self.props = Props()
        super(Pie,self).__init__(Axes_Square=True)
    
    def data(self):
        axes = self.figure.gca()
        series = self.props.series
        
        labels = [item['label'] for item in series]
        value = [item['value'] for item in series]
        colour = [item['colour'] for item in series]
        explode = [item['explode'] for item in series]
        
        
        axes.pie(value, 
                 explode=explode, 
                 labels=labels, 
                 autopct='%1.1f%%' if self.props.percentage else None, 
                 shadow=self.props.shadow, 
                 colors=colour)
