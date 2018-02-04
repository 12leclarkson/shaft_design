import sqlite3
from math import pi

conn = sqlite3.connect('Bearings.db')   # connect to the bearing db
db = conn.cursor()
bearingList = []    # set empty list for first selection to be stored in

db.execute("SELECT f0_Fa_C0 FROM cal_factors ")  # get correction factors from db
cal_factors_data = db.fetchall()
cal_factors = []
for i in cal_factors_data:
    # convert db data to a usable form
    cal_factors.append(i[0])


class Bearing(object):
    # Define the bearing class
    def __init__(self, D_lower, D_upper, B, C, C0, Pu, reference_speed, limiting_speed, mass, designation, D_lower_1,
                 D_upper_1,
                 D_upper_2, r1_2_min, D_lower_a_min, D_upper_a_max, ra_max, kr, f0):
        # set properties of the bearing
        self.D_lower = D_lower
        self.D_upper = D_upper
        self.B = B
        self.C = C
        self.C0 = C0
        self.Pu = Pu
        self.reference_speed = reference_speed
        self.limiting_speed = limiting_speed
        self.mass = mass
        self.designation = designation
        self.D_lower_1 = D_upper_1
        self.D_upper_2 = D_upper_2
        self.r1_2_min = r1_2_min
        self.D_lower_a_min = D_lower_a_min
        self.D_upper_a_max = D_upper_a_max
        self.ra_max = ra_max
        self.kr = kr
        self.f0 = f0


def get_inputs():
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


def get_bearings(d, D, f_a, f_r, l_ten):
    if D == '':
        # no outer diameter given
        db.execute("SELECT * FROM SKF_Single_Row_Deep_Groove_Bearings_Final WHERE D_lower = ?", (d,))
    elif d == '':
        # no inner diameter given
        db.execute("SELECT * FROM SKF_Single_Row_Deep_Groove_Bearings_Final WHERE D_upper = ?", (D,))
    else:
        # if the outer diameter is smaller than the inner (impossible!)
        if int(D) <= int(d):
            print "\nShaft diameter must be smaller than outer diameter "
        else:
            # case when both inner & outer diameter are given
            db.execute("SELECT * FROM SKF_Single_Row_Deep_Groove_Bearings_Final WHERE D_lower = ? AND D_upper = ?", (d, D))
    fetchedBearings = db.fetchall()

    for bearing in fetchedBearings:
        new_bearing = Bearing(bearing[0], bearing[1], bearing[2], bearing[3], bearing[4], bearing[5], bearing[6],
                              bearing[7],
                              bearing[8], bearing[9], bearing[10], bearing[11], bearing[12], bearing[13], bearing[14],
                              bearing[15],
                              bearing[16], bearing[17], bearing[18])
        bearingList.append(new_bearing)
    if not bearingList:
        # if bearing list is empty, i.e. don't have the size etc.
        print '\nNo bearings with those diameters, try with different sizes!\n'
    else:
        bearingList.sort(key=lambda x: x.C)  # ascending sort of the selected bearings based on C
        c_values = []
        bearing_candidates = []
        (c, case) = get_forces(f_a, f_r, l_ten)
        c = round(c / 1000.0, 2)
        print '\nPre-lim suitable bearings: '
        for i in bearingList:  # cycle through bearings that were selected by diameter
            if c < i.C:  # check the c rating for the bearing vs calculated c
                db.execute(
                    "SELECT * FROM SKF_Single_Row_Deep_Groove_Bearings_Final WHERE C = ? AND D_lower = ? ",
                    (i.C, d,))  # select  from db
                data = db.fetchall()
                if not data:  # no bearings case
                    break
                for a_bearing in data:
                    prelim_bearing = Bearing(a_bearing[0], a_bearing[1], a_bearing[2], a_bearing[3], a_bearing[4],
                                             a_bearing[5],
                                             a_bearing[6],
                                             a_bearing[7],
                                             a_bearing[8], a_bearing[9], a_bearing[10], a_bearing[11], a_bearing[12],
                                             a_bearing[13],
                                             a_bearing[14],
                                             a_bearing[15],
                                             a_bearing[16], a_bearing[17], a_bearing[18])
                    bearing_candidates.append(prelim_bearing)  # add data to candidate list
                    c_values.append(prelim_bearing.C)
                    print prelim_bearing.designation
        check(bearing_candidates, f_a, f_r, l_ten, case)


def get_forces(f_a, f_r, l_ten):
    if f_r == 0 and f_a != "":
        # case if f_r = 0 and f_a has value
        f = f_a
        case = 1
    elif f_a == 0 and f_r != "":
        print 'case 2'
        # case if f_a = 0 and f_r has value
        f = f_r
        case = 2
    else:
        # case if f_a and f_r have values
        # use larger force to find c for worst case scenario
        if f_a >= f_r:
            f = f_a
        else:
            f = f_r
        case = 3

    print '\nUncorrected force: ', int(f), 'N'
    c = f * l_ten ** (1.0 / 3.0)

    return (c, case)


def check(bearing_candidates, f_a, f_r, l_ten, case):
    # check if the original bearings selected are still usable (base selection on forces, not just diameter)
    good_bearings = []  # create empty list to store bearings that are suitable (after this test)
    for factor in cal_factors_data:
        # convert db data to a usable form
        cal_factors.append(factor[0])
    good_bearings = []
    if case == 1 or case == 2:
        print 'No force correction needed because one force was given'
        print 'Usable bearings:'
        for checked in bearing_candidates:
            print checked.designation
        exit()
    elif case == 3:
        print '\nNow checking if selection is still appropriate'
        for bearing in bearing_candidates:
            print good_bearings
            print '\n', bearing.designation
            adjustment = float((bearing.f0 * f_a) / (bearing.C0 * 1000.0))  # this is r, r = f0*fa/C0
            #print '\n', bearing.designation
            #print 'adj', adjustment

            for var in cal_factors:  # for each correction factor value in db
                #print var
                if adjustment < var:  # if the r value is < the current table value of fr_Fa_C0 from db
                    closest_f0 = var  # the closest value of f0 = current correction factor
                    # this loop selects the upper and lower values to interpolate for e
                    #print 'adjustment < var'
                    db.execute(
                        "SELECT f0_Fa_C0, e_N,X_N,Y_N FROM cal_factors WHERE f0_Fa_C0 <=? ORDER BY f0_Fa_C0 DESC LIMIT 2 ",
                        (closest_f0,))  # get the upper and lower values for e
                    data = db.fetchall()
                    #print data
                    try:
                        e = data[0][1] + (adjustment - data[0][0]) / (data[1][0] - data[0][0]) * (data[1][1] - data[0][1])
                        # calculate e by interpolation!
                        print 'e', e
                        if f_a / f_r <= e:
                            #print 'fa/fr <= e'
                            # if the ratio of the axial/radial force is < e, set correction factors as y = 1, x = 0
                            # i.e. there is no change in the force used to select the bearing
                            # X = 1
                            # Y = 0
                            # f_new = X * f_r + Y * f_a
                            f_new = f_r
                            print 'No force adjustment for', bearing.designation
                            good_bearings.append(bearing.designation)
                            break
                        else:
                            #print 'fa/fr > e'
                            # if the ratio of the axial/radial force is > e, set correction factors via interpolation
                            # i.e. there is a change in the force used to select the bearing
                            X = 0.56
                            Y = data[1][3] + ((adjustment - data[1][0]) / (data[0][0] - data[1][0])) * (
                                    data[0][3] - data[1][3])
                            f_new = X * f_r + Y * f_a
                            c_min = f_new * l_ten ** (1.0 / 3.0)
                            if c_min / 1000 <= bearing.C:  # compare the new cmin value to the actual bearing value
                                good_bearings.append(bearing.designation)  # add to usable bearings if condition is met
                                break
                            else:
                                # this bearing is no longer suitable
                                print bearing.designation, 'is not suitable when axial force is considered'
                                break
                    except IndexError:
                        print "The value of adjustment to interpolate for e is outside of the range of the " \
                              "data we have!" \
                              "\nmoving onto the next bearing and excluding this one"


                else:  # if the r value is greater than the current correction factor, try the next value
                    pass

        print '\nThe corrected force =', int(f_new), 'N\n'  # return the corrected force
        if good_bearings:
            # print the usable bearings in the list
            print 'Usable bearings:'
            for checked in good_bearings:
                print checked
            exit()
        else:
            print 'No bearings are suitable for this situations\nRetry with different values\n'


def __main__():
    iteration = 1
    while True:
        print 'Iteration', iteration
        input_data = get_inputs()  # get inputs and put into usable list
        # insert the list to usable variables
        d = input_data[0]
        D = input_data[1]
        part_dia = input_data[2]
        life = input_data[3]
        use = input_data[4]
        f_r = input_data[5]
        f_a = input_data[6]
        vel = input_data[7]
        use_time = use * life * 365 * 60  # convert use time to seconds
        revs = 60 * vel / (part_dia * pi)  # calculate the revolutions from diameter of part and velocity
        l_ten = (use_time * revs) / 1000000  # calculate L10
        get_bearings(d, D, f_a, f_r, l_ten)
        iteration += 1


__main__()
