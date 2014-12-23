class LogBin():
    def __init__(area_max, area_min):
        self.area_min = area_min
        self.area_max = area_max

class LogMesh():
    def __init__(area_max, levels):
        self.area_max = area_max
        
        self.bins = []
        for i in range(levels):
            area_min = area_max * 0.5
            self.bins.append(LogBin(area_max, area_min))
            
            area_max = area_min
            
    
