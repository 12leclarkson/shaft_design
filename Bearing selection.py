import sqlite3
from math import pi

# column names
# D_lower,D_upper,B,C,C0,Pu,reference_speed,limiting_speed ,mass, designation,D_lower_1,D_upper_1,D_upper_2,r1_2_min,D_lower_a_min,D_upper_a_max,ra_max,kr,f0

# sqlite db connection
conn = sqlite3.connect('Bearings.db')
db = conn.cursor()


# return string from db
def sqlprint(string):
    try:
        return str(string)
    except:
        return None


def getInputs():
    # user prompts
    prompts = ["Shaft diameter (mm): ", "Outer diameter (mm): ", "Part diameter (m): ", "Design life (years): ",
               "Average use per day (hours): ", "Radial force (N): ", "Axial force (N): ", "Average velocity (m/s): "]
    variables = []  # list of data
    for prompt in prompts:  # cycle through the prompts
        while True:  # don't stop till you get a usable value
            try:  # check if input is of the right type
                if prompts.index(prompt) == 0 or prompts.index(prompt) == 1:
                    # special case for inner/outer bearing diameter
                    variable = raw_input(prompt)
                    if variable != '':
                        # if inner/outer bearing diameter isn't none, try to change to int
                        variable = int(variable)
                    else:
                        # if inner/outer bearing diameter is none, don't try to change to int
                        pass
                else:  # other cases, convert to float
                    variable = float(raw_input(prompt))
                variables.append(variable)  # add to variables list
                break  # go to next prompt

            except ValueError:  # raise error when you don't enter numbers
                print 'Sorry, you need to input a number'
                continue
    return variables  # return the list


ins = getInputs()  # get inputs and put into usable list

# insert the list to usable variables
d = ins[0]
D = ins[1]
partDia = ins[2]
life = ins[3]
use = ins[4]
f_r = ins[5]
f_a = ins[6]
vel = ins[7]

if D == '':
    # no outer diameter given
    db.execute("SELECT C FROM SKF_Single_Row_Deep_Groove_Bearings WHERE D_lower = ?", (d,))
    bearings = db.fetchall()


elif d == '':
    # no inner diameter given
    db.execute("SELECT C FROM SKF_Single_Row_Deep_Groove_Bearings WHERE D_upper = ?", (D,))
    bearings = db.fetchall()

else:
    # if the outer diameter is smaller than the inner (impossible!)
    if int(D) <= int(d):
        print "Shaft diameter must be smaller than outer diameter "
    else:
        # case when both inner & outer diameter are given
        db.execute("SELECT C FROM SKF_Single_Row_Deep_Groove_Bearings WHERE D_lower = ? AND D_upper = ?", (d, D))
        bearings = db.fetchall()
useTime = use * life * 365 * 60  # convert use time to seconds
revs = 60 * vel / (partDia * pi)  # calculate the revolutions from diameter of part and velocity
l = (useTime * revs) / 1000000  # calculate L10


def check(bearing_candidates, f_a, f_r, l):
    # check if the original bearings selected are still usable (base selection on forces, not just diameter)
    print '\nNow checking if selection is still appropriate'
    db.execute("SELECT f0_Fa_C0 FROM cal_factors ")  # get correction factors from db
    cal_factors_data = db.fetchall()
    cal_factors = []
    for i in cal_factors_data:
        # convert db data to a usable form
        cal_factors.append(i[0])
    good_bearings = []
    for i in bearing_candidates:  # while we have bearing candidates to test

        for j in i:  # take the first column in i (sqlite returns as multi-dimension list)
            # j format: designation, C0, f0, C
            print 'checking', j[0], j[3]
            adjustment = float((j[2] * f_a) / (j[1] * 1000.0))  # this is r, r = f0*fa/C0
            print 'adj', adjustment
            for var in cal_factors:  # for each correction factor value in db

                print 'var', var
                if adjustment < var:  # if the r value is < the current table value of fr_Fa_C0 from db
                    closest_f0 = var  # the closest value of f0 = current correction factor
                    # this loop selects the upper and lower values to interpolate for e
                    db.execute(
                        "SELECT f0_Fa_C0, e_N,X_N,Y_N FROM cal_factors WHERE f0_Fa_C0 <=? ORDER BY f0_Fa_C0 DESC LIMIT 2 ",
                        (closest_f0,))  # get the upper and lower values for e
                    data = db.fetchall()
                    print 'all the crap: ', data[0][1], adjustment, data[0][0], data[1][0], data[0][0], data[1][1], \
                        data[0][1]
                    e = data[0][1] + (adjustment - data[0][0]) / (data[1][0] - data[0][0]) * (data[1][1] - data[0][1])
                    # calculate e by interpolation!
                    print 'e', e
                    if f_a / f_r <= e:
                        # if the ratio of the axial/radial force is < e, set correction factors as y = 1, x = 0
                        # i.e. there is no change in the force used to select the bearing
                        X = 1
                        Y = 0
                        f_new = X * f_r + Y * f_a
                        print 'No change!'
                    else:
                        # if the ratio of the axial/radial force is > e, set correction factors via interpolation
                        # i.e. there is a change in the force used to select the bearing
                        X = 0.56
                        Y = data[1][3] + ((adjustment - data[1][0]) / (data[0][0] - data[1][0])) * (
                            data[0][3] - data[1][3])
                        f_new = X * f_r + Y * f_a
                        c_min = f_new * l ** (1.0 / 3.0)
                        if c_min / 1000 <= j[3]:  # compare the new cmin value to the actual bearing value
                            good_bearings.append(j[0])  # add to usable bearings if condition is met
                            break
                        else:
                            # this bearing is no longer suitable
                            print j[0], 'is not suitable when axial force is considered'
                            break
                else:  # if the r value is greater than the current correction factor, try the next value
                    pass

    print '\nThe corrected force =', int(f_new), 'N\n'  # return the corrected force
    if good_bearings:
        # print the usable bearings in the list
        print 'Usable bearings:'
        for i in good_bearings:
            print i
    else:
        print 'No bearings are suitable for this situations'


if f_r == 0 and f_a != "":
    # case if f_r = 0 and f_a has value
    f = f_a
    c = f * l ** (1.0 / 3.0)
elif f_a == 0 and f_r != "":
    # case if f_a = 0 and f_r has value
    f = f_r
    c = f * l ** (1.0 / 3.0)
elif f_a != "" and f_r != "":
    # case if f_a and f_r have values
    # use larger force to find c
    if f_a >= f_r:
        c = f_a * l ** (1.0 / 3.0)
    else:
        c = f_r * l ** (1.0 / 3.0)
else:
    # case if f_a and f_r = 0
    print "Must have a force"

c = round(c / 1000.0, 2)
# c -> round & put into kN so we can compare the worst case scenario
# (better safe than sorry, take the highest value of c)
if not bearings:
    # if bearing list is empty, i.e. don't have the size etc.
    print 'No bearings'

else:
    bearings.sort()

    print '\nPre-lim suitable bearings: '
    c_values = []
    bearing_candidates = []
    for i in bearings:  # cycle through dia selected bearings
        if c < i[0]:  # check the c rating for the bearing vs calculated c
            db.execute(
                "SELECT designation, C0, f0, C FROM SKF_Single_Row_Deep_Groove_Bearings WHERE C = ? AND D_lower = ? ",
                (i[0], d,))  # select C0, f0, C from db
            data = db.fetchall()
            if not data:  # no bearings case
                break
            for a in data:
                bearing_candidates.append(data)  # add data to candidate list
                c_values.append(a[1])
                print a[0]

        else:
            pass
    if not c_values:
        # if there are no c values
        print 'No bearings'
    else:

        check(bearing_candidates, f_a, f_r, l)  # use forces to double check if selection will be okay
