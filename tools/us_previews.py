# Renders high-res preview pages of the "Printable Calendar for 2027 - Minimal" product (Sunday start, US federal holidays in orange)
import calendar, datetime as dt
from PIL import Image, ImageDraw, ImageFont
import os, urllib.request
FD=[ '/usr/share/fonts/truetype/google-fonts/', os.path.join(os.path.dirname(os.path.abspath(__file__)),'fonts/')]
def f(w,s):
    for d in FD:
        if os.path.exists(d+f'Poppins-{w}.ttf'): return ImageFont.truetype(d+f'Poppins-{w}.ttf',s)
    try:
        os.makedirs(FD[1],exist_ok=True); open(FD[1]+f'Poppins-{w}.ttf','wb').write(urllib.request.urlopen(f'https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-{w}.ttf',timeout=20).read()); return ImageFont.truetype(FD[1]+f'Poppins-{w}.ttf',s)
    except: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'%('-Bold' if w in('Bold','SemiBold') else ''),s)
ORANGE=(232,121,52); INK=(34,34,34); GREY=(140,140,140); LINE=(215,215,215)
HOL={(1,1):"New Year's Day",(1,18):'MLK Jr. Day',(2,15):"Washington's Birthday",(5,31):'Memorial Day',(6,19):'Juneteenth',(7,4):'Independence Day',(9,6):'Labor Day',(10,11):'Columbus Day',(11,11):'Veterans Day',(11,25):'Thanksgiving',(12,25):'Christmas Day'}
cal=calendar.Calendar(firstweekday=6)
def year_page(W=1700,H=2200):
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im)
    d.text((W/2,120),'2027',font=f('Bold',120),fill=INK,anchor='mm')
    d.text((W/2,215),'Year at a Glance  ·  Sunday start  ·  US federal holidays in orange',font=f('Regular',30),fill=GREY,anchor='mm')
    mx,my,gx,gy=90,300,40,45; cw=(W-2*mx-2*gx)/3; ch=(H-my-160-3*gy)/4
    for m in range(1,13):
        c=(m-1)%3; r=(m-1)//3; x=mx+c*(cw+gx); y=my+r*(ch+gy)
        d.rectangle([x,y,x+cw,y+ch],outline=LINE,width=2)
        d.text((x+18,y+14),calendar.month_name[m],font=f('SemiBold',34),fill=INK)
        cellw=(cw-36)/7
        for i,n in enumerate('SMTWTFS'):
            d.text((x+18+cellw*i+cellw/2,y+78),n,font=f('Medium',22),fill=GREY,anchor='mm')
        for wi,week in enumerate(cal.monthdayscalendar(2027,m)):
            for di,day in enumerate(week):
                if not day: continue
                cx=x+18+cellw*di+cellw/2; cy=y+120+wi*44
                if (m,day) in HOL:
                    d.ellipse([cx-19,cy-19,cx+19,cy+19],fill=ORANGE); d.text((cx,cy),str(day),font=f('SemiBold',24),fill='white',anchor='mm')
                else: d.text((cx,cy),str(day),font=f('Regular',24),fill=INK,anchor='mm')
    d.text((W/2,H-70),'2027 Printable Calendar  ·  Maya More',font=f('Regular',24),fill=GREY,anchor='mm')
    return im
def month_page(m,W=2200,H=1700):
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im)
    d.text((110,90),calendar.month_name[m],font=f('Bold',96),fill=INK)
    d.text((110+d.textlength(calendar.month_name[m],font=f('Bold',96))+30,128),'2027',font=f('Regular',64),fill=GREY)
    top=300; left=110; gw=W-220; cw=gw/7; weeks=cal.monthdayscalendar(2027,m); rh=(H-top-170)/len(weeks)
    for i,n in enumerate(['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']):
        d.text((left+cw*i+cw/2,top-40),n,font=f('Medium',30),fill=GREY,anchor='mm')
    for wi,week in enumerate(weeks):
        for di,day in enumerate(week):
            x=left+di*cw; y=top+wi*rh
            d.rectangle([x,y,x+cw,y+rh],outline=LINE,width=2)
            if day:
                hol=(m,day) in HOL
                d.text((x+18,y+12),str(day),font=f('SemiBold',38),fill=ORANGE if hol else INK)
                if hol: d.text((x+18,y+62),HOL[(m,day)],font=f('Medium',24),fill=ORANGE)
    d.text((110,H-80),'2027 Printable Calendar  ·  Maya More',font=f('Regular',26),fill=GREY)
    return im
year_page().save('us_year.png'); month_page(7).save('us_july.png'); month_page(11).save('us_nov.png'); month_page(1).save('us_jan.png')
print('ok')
