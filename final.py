import pymurapi as mur
import cv2
import numpy as np
import math
import time

auv = mur.mur_init()

def wait(t):
    ntt = time.time()
    while  time.time() - ntt < t/10:          
        auv.set_motor_power(0, 0)
        auv.set_motor_power(1, 0)
        auv.set_motor_power(2, 0)
        auv.set_motor_power(3, 0)
        auv.set_motor_power(4, 0) 
        if time.time() - ntt > t/1000:
           break 

# Перевод угла >< 360 в 0 <=> 360
def clamp_to_360(angle):
    if angle < 0.0:
        return angle + 360.0
    if angle > 360.0:
        return angle - 360.0
    return angle

# Перевод угла из 0 <=> 360 в -180 <=> 180
def to_180(angle):
    if angle > 180.0:
        return angle - 360.0
    return angle

# Преобразовать v в промежуток между min max
def clamp(v, min, max):
    if v < min:
        return min
    if v > max:
        return max
    return v

# Функция удержания курса
def keep_yaw(yaw_to_set = 0.0, power = 0):
    current_yaw = auv.get_yaw()    
    er = clamp_to_360(float(yaw_to_set) - current_yaw)
    er = to_180(er)
    res = er * -1*kpy
    auv.set_motor_power(0, clamp(int(power - res), -100, 100))
    auv.set_motor_power(1, clamp(int(power + res), -100, 100))


def keep_depth(depth_to_set, kpd):
    power = kpd * (auv.get_depth() - depth_to_set)
    auv.set_motor_power(2, clamp(int(power), -100, 100))
    auv.set_motor_power(3, clamp(int(power), -100, 100))    

# ЦВЕТОВОЙ ФИЛЬТР
def color_mask(image, color):
    img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    if color == "red":
        lower = np.array([23,30,20])
        upper = np.array([33,255,655])
        mask = cv2.inRange(img_hsv, lower, upper)
    if color == "green":
        lower = np.array([46,14,0])
        upper = np.array([100,555,755])
        mask = cv2.inRange(img_hsv, lower, upper)
    return mask
      
def detected_colors_list(image, size = 50):
    clr_list = []
    for clr in colors:
        mask = color_mask(image, clr)
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > size:
                clr_list.append(clr)
    return clr_list            
                

# распознавание и центровка по объекту           
def obj_centering(image,color, sdvig = 0,small = 50, big = 80000):
    global power0
    powerD = 0
    mask = color_mask(image, color)  
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(mask, contours, -1, (128,0,0), 1) #cv2.FILLED,    
    rectx = 0
    recty = 0  
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area <= small or area  > big:  
            continue 
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

 # вычисление координат двух векторов, являющихся сторонам прямоугольника
        edge1 = np.int0((box[1][0] - box[0][0],box[1][1] - box[0][1]))
        edge2 = np.int0((box[2][0] - box[1][0], box[2][1] - box[1][1]))
        if cv2.norm(edge2) / cv2.norm(edge1) > 7 or cv2.norm(edge2) / cv2.norm(edge1) < 0.14:
            continue
                  
        cv2.drawContours(image,[box],0,(0,0,0),2) # рисуем прямоугольник
        rectx, recty = (int(rect[0][0]),int(rect[0][1]))           
        if rectx < (xCenter - indent):  
           powerD = kx*(xCenter - (indent + rectx))
        if rectx > (xCenter + indent):
           powerD = (-1)*kx*(rectx - (xCenter + indent))
        if recty < (yCenter + sdvig - indent):
           power0 = ky*(yCenter + sdvig - (indent + recty))
        if recty > (yCenter + sdvig + indent):
           power0 = (-1)*ky*(recty - (yCenter + sdvig + indent))
    auv.set_motor_power(4, int(powerD)) 
               
    cv2.imshow("Image2",image)
    cv2.waitKey(5)                  
    cv2.imshow("Image3", mask)
    cv2.waitKey(5)
    if abs(xCenter - rectx) < 5:
        auv.set_motor_power(4, 0) 
    if abs(yCenter + sdvig - recty) < 5:
        power0 = 0
    if (abs(xCenter - rectx) < 35 and abs(yCenter + sdvig - recty) < 15):
        auv.set_motor_power(4, 0) 
        power0 = 0     
        return True
    else: 
        return False

# ВЫЧИСЛЕНИЕ РАЗМЕРА ОБЪЕКТА       
def rotate_to_arrow(image, color, small = 150, big = 10000):
    global powerR
    mask = color_mask(image, color)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(mask, contours, -1, (128,0,0), 1) #cv2.FILLED,
    rectx = 0
    recty = 0  
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area <= small or area > big:  
            continue 
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        cv2.drawContours(image,[box],0,(0,0,0),2) # рисуем прямоугольник
        rectx, recty = (int(rect[0][0]),int(rect[0][1]))       

        if rectx < (xCenter - indent) and rectx > 20:               
           powerR = -0.04*(xCenter - (indent + rectx))
        if rectx > (xCenter + indent) and rectx < 140:
                  powerR = (0.04)*(rectx - (xCenter + indent))
         
    cv2.imshow("Image2",image)
    cv2.waitKey(5)                  
    cv2.imshow("Image3", mask)
    cv2.waitKey(5)
    if abs(xCenter - rectx) < 20 and recty < 110:
        powerR = 0    
        return True           
    else:
           return False
           
# ПОВОРОТ К НАЙДЕННОМУ ОБЪЕКТУ         
def rotate_to_obj(image, color, small = 150, big = 10000, tol = 25):
    global powerR
    mask = color_mask(image, color)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(mask, contours, -1, (128,0,0), 1) #cv2.FILLED,
    rectx = 0
    recty = 0  
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area <= small or area > big:  
            continue 
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        cv2.drawContours(image,[box],0,(0,0,0),2) # рисуем прямоугольник
        rectx, recty = (int(rect[0][0]),int(rect[0][1]))       

        if rectx < (xCenter - indent) and rectx > 25:               
           powerR = -0.12*(xCenter - (indent + rectx))
        if rectx > (xCenter + indent) and rectx < 140:
           powerR = (0.12)*(rectx - (xCenter + indent))
         
    cv2.imshow("Image2",image)
    cv2.waitKey(5)                  
    cv2.imshow("Image3", mask)
    cv2.waitKey(5)
    if abs(xCenter - rectx) < tol:
        powerR = 0    
        return True           
    else:
        return False
       
def rotate_to_cube(image, color, small = 100, big = 10000, tol = 5):
    global powerR
    mask = color_mask(image, color)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(mask, contours, -1, (128,0,0), 1) #cv2.FILLED,
    rectx = 0
    recty = 0  
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area <= small or area > big:  
                   continue                    
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
                         
    # вычисление координат двух векторов, являющихся сторонами прямоугольника
        edge1 = np.int0((box[1][0] - box[0][0],box[1][1] - box[0][1]))
        edge2 = np.int0((box[2][0] - box[1][0], box[2][1] - box[1][1]))
        if cv2.norm(edge2) / cv2.norm(edge1) > 1.25 or cv2.norm(edge2) / cv2.norm(edge1) < 0.8:
            continue
           
         
        cv2.drawContours(image,[box],0,(0,0,0),2) # рисуем прямоугольник
        rectx, recty = (int(rect[0][0]),int(rect[0][1]))
        if rectx < (xCenter - indent) and rectx > 20:               
           powerR = -0.12*(xCenter - (indent + rectx))
        if rectx > (xCenter + indent) and rectx < 140:
           powerR = (0.12)*(rectx - (xCenter + indent))
    cv2.imshow("Image2",image)
    cv2.waitKey(5)                  
    cv2.imshow("Image3", mask)
    cv2.waitKey(5)
    if abs(xCenter - rectx) < tol:
        powerR = 0    
        return True           
    else:
        return False


          
def vpered(col, dts, yts3, power): 
    while True:
        keep_yaw(yts3, power)
        keep_depth(dts, kpd)
        mask = color_mask(auv.get_image_bottom(), col)
        ls = []  
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(mask, contours, -1, (128,0,0), 1) 
        cv2.imshow("Image3", mask)
        cv2.waitKey(5)
        ls = detected_colors_list(auv.get_image_bottom(), 50)
        if col not in ls:
            return
            
       
                  
         




def zahvat(image, color, dts):
    dcurrent = auv.get_depth()
    powerD = 0
    nx_color = '' 
    while dcurrent < 2.6:        
        auv.set_motor_power(2, -20)
        auv.set_motor_power(3, -20)
        dcurrent = auv.get_depth()
        print(dcurrent)
    while dcurrent < 3.55 and dcurrent < dts:
        sm = -1*(dcurrent - 2.7)*35                   
        obj_centering(auv.get_image_bottom(), color, sm, 200)
        auv.set_motor_power(2, -8)
        auv.set_motor_power(3, -8)
        keep_yaw(yts, power0)
        dcurrent = auv.get_depth()
 
    while dcurrent < dts:           
        auv.set_motor_power(2, -25)
        auv.set_motor_power(3, -25)       
        dcurrent = auv.get_depth()
        if dcurrent > 3.6:
            ls = detected_colors_list(image, 1000)
            for x in ls:
                if x != color:
                    nx_color = x
    return nx_color 
   
def vozvr_centr():
    global power0
    powerR = 12
    directed = False
    nnn =  time.time()
    while  time.time() - nnn < 0.6:
       keep_depth(1.9, kpd*2)
       auv.set_motor_power(0, 90)
       auv.set_motor_power(1, -90) 
    while not directed:
       keep_depth(1.9, kpd)
       directed = rotate_to_arrow(auv.get_image_bottom(), 'orange', 50)
       auv.set_motor_power(0, powerR)
       auv.set_motor_power(1, -1*powerR)       
    print('Directed to orange arrow')
    
    power0 = 10
    y = auv.get_yaw()
    ytss = to_45 (y)        
    dts1 = 2.7
    vpered( 'orange', dts1, ytss, powv)
    centred =False # центровка по центральной стрелке
    n1 = time.time()
    while not centred or (time.time() - n1) < 3:
        centred = obj_centering(auv.get_image_bottom(), 'orange',0 ,50 )   
        keep_depth(dts,  kpd)
        keep_yaw(ytss, power0)       
    print('Centered')

def to_45(y):
    if y > 2 and y < 87:
        a = 45.0
    elif y > 92 and y < 179:
         a = 135.0
    elif y < -2  and y > -87:
        a = -1*45.0
    elif y < -92 and y > -179:
        a = -1*135.0
    else:
        a = y
    return a
       
def razgon_obj(color):
    tm = time.time() 
    powerR = powr
    dir = False
    while not dir:
        keep_depth(dts3, kpd)
        dir = rotate_to_obj(auv.get_image_front(), color, 300, tol = 130)
        auv.set_motor_power(0, 60)
        auv.set_motor_power(1, -60)
    if time.time()-tm > 0.3:
        tm1 = time.time() 
        while time.time()-tm1 < 0.45:
            auv.set_motor_power(0, -60)
            auv.set_motor_power(1, 60)

def razgon_cube(color):
    tm = time.time() 
    powerR = powr
    dir = False
    while not dir:
        keep_depth(dts4, kpd)
        dir = rotate_to_cube(auv.get_image_front(), color, 80, 200, tol = 100)
        auv.set_motor_power(0, 60)
        auv.set_motor_power(1, -60)
    if time.time()-tm > 0.45:
        tm1 = time.time() 
        while time.time()-tm1 < 0.6:
            auv.set_motor_power(0, -60)
            auv.set_motor_power(1, 60)   
    

if __name__ == '__main__': 
    
    
    print  ('start')
    start = time.time()
    colors = ['red', 'blue', 'orange', 'yellow', 'green']
    kpy = 0.1
    kpd = 17
    kx, ky = 0.3, 0.12
    indent = 2;
    xCenter = 160;
    yCenter = 120;  
#    tc, tr, tk, tp = 4.5, 3, 4.4, 6.0
    powv, pow0, powr, powup = 80, 30, 10, 20
    dts2, dts3, dts4 = 2.5, 3.1, 2.9   


    dts = 2.5
    yts = auv.get_yaw()
    nt = time.time()
    while time.time() - nt < 1:
        auv.set_motor_power(0, 80)
        auv.set_motor_power(1, 80)
    
# ищем желтый кубик
    color = 'red'    
    powerR = powr
    dts = dts4
    razgon_cube(color)
    directed = False
    while not directed:
       keep_depth(dts, kpd)
       directed = rotate_to_cube(auv.get_image_front(), color, 100, 200)
       auv.set_motor_power(0, powerR)
       auv.set_motor_power(1, -1*powerR)
    print('Directed to yellow cube')

    yts = auv.get_yaw() 
    vpered(color ,dts, yts, powv)
    dts = dts2
    power0 = pow0
    centred =False
    n = time.time()
    while not centred or (time.time() - n ) < 8:
        centred = obj_centering(auv.get_image_bottom(), color, 0)   
        keep_depth(dts,  kpd)
        keep_yaw(yts,power0)       
    print('Centered')
    
    #берем желтый кубик
    auv.open_grabber()
    nx_color = zahvat(auv.get_image_bottom(), color,3.61)
    auv.close_grabber()
    nt = time.time()
    while  (time.time() - nt) < 1:
           keep_depth(3.62, kpd)
           
            
# Ищем казину
    dts = dts3   
    powerR = powr
    color = 'green'
    directed = False
    while not directed:
        keep_depth(dts, kpd)
        directed = rotate_to_obj(auv.get_image_front(), color)
        auv.set_motor_power(0, powerR)
        auv.set_motor_power(1, -1*powerR)
    print('Directed to orange post',powerR)

    yts = auv.get_yaw()       
    dts = 1.5
    vpered('green',dts, yts, 80)
    power0 = pow0
    centred =False
    n = time.time()
    while not centred and (time.time() - n < 10):
        centred = obj_centering(auv.get_image_bottom(), color)   
        keep_depth(dts,  kpd)
        keep_yaw(yts,power0)       
    print('Centered')

    while dcurrent > 0:        
        auv.set_motor_power(2, 50)
        auv.set_motor_power(3, 50)       
        dcurrent = auv.get_depth()
