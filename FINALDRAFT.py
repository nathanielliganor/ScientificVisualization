import json
import numpy as np
import pandas as pd
from collections import defaultdict
import altair as alt

import warnings
warnings.filterwarnings('ignore')

# loading the events data
events = {}
nations = ['Italy', 'England', 'Germany', 'France', 'Spain', 'European_Championship', 'World_Cup']
for nation in nations:
    with open('C:\\Users\\Nathaniel L\\Desktop\\Data\\events\\events_%s.json' % nation) as json_data:
        events[nation] = json.load(json_data)

# loading the match data
matches = {}
nations = ['Italy', 'England', 'Germany', 'France', 'Spain', 'European_Championship', 'World_Cup']
for nation in nations:
    with open('C:\\Users\\Nathaniel L\\Desktop\\Data\\matches\\matches_%s.json' % nation) as json_data:
        matches[nation] = json.load(json_data)

# loading the players data
players = {}
with open('C:\\Users\\Nathaniel L\\Desktop\\Data\\players.json') as json_data:
    players = json.load(json_data)

# loading the competitions data
competitions = {}
with open('C:\\Users\\Nathaniel L\\Desktop\\Data\\competitions.json') as json_data:
    competitions = json.load(json_data)


def in_window(events_match, time_window):
    start, end = events_match[0], events[-1]
    return start['eventSec'] >= time_window[0] and end['eventSec'] <= time_window[1]


def get_invasion_index(db, match_id, lst=False):
    """
    Compute the invasion index for the input match

    Parameters
    ----------
    match_id: int
        the match_id of the match for which we want the invasion index

    Returns
    -------
    invasion_index: float
        the invasion index of the two teams, the list of invasion acceleration
        for each possesion phase of each team
    """
    actions = get_play_actions(db, match_id)
    team2invasion_index = defaultdict(list)
    team2invasion_speed = defaultdict(list)
    events_match = []
    for nation in nations:
        for ev in events[nation]:
            if ev['matchId'] == match_id:
                events_match.append(ev)
    half_offset = {'2H': max([x['eventSec'] for x in events_match if x['matchPeriod'] == '1H']),
                   '1H': 0}
    events_match = sorted(events_match, key=lambda x: x['eventSec'] + half_offset[x['matchPeriod']])
    off = half_offset['2H']
    times_all = []
    for action in actions:
        action_type, events_match = action
        offset = off if events_match[0]['matchPeriod'] == '2H' else 0
        if len(set([x['matchPeriod'] for x in events_match])) > 1:
            continue
        team_id = events_match[0]['teamId']
        all_weights, times = [], []
        for event in events_match:
            try:
                x, y, s = int(event['positions'][0]['x']), int(event['positions'][0]['y']), event['eventSec']
            except:
                continue  # skip to next event in case of missing position data
            all_weights.append(get_weight((x, y)))
            # all_weights.append(get_datadriven_weight((x, y)))
            times.append(s)

        times_maxinv = sorted(times, key=lambda x: all_weights[times.index(x)], reverse=True)[0]
        seconds = times_maxinv - events_match[0]['eventSec']
        if seconds > 0.8:
            team2invasion_speed[team_id] += [
                (events_match[0]['eventSec'] + offset, (np.max(all_weights) - all_weights[0]) / seconds ** 2)]

        team2invasion_index[team_id] += [(events_match[0]['eventSec'] + offset, np.max(all_weights))]

    if not lst:
        team2invasion_index = {k: [x for x in v] for k, v in team2invasion_index.items()}
        team2invasion_speed = {k: [x for x in v] for k, v in team2invasion_speed.items()}

    return team2invasion_index, team2invasion_speed


def segno(x):
    """
    Input:  x, a number
    Return:  1.0  if x>0,
            -1.0  if x<0,
             0.0  if x==0
    """
    if x > 0.0:
        return 1.0
    elif x < 0.0:
        return -1.0
    elif x == 0.0:
        return 0.0


def standard_dev(list):
    ll = len(list)
    m = 1.0 * sum(list) / ll
    return (sum([(elem - m) ** 2.0 for elem in list]) / ll) ** 0.5


def list_check(lista):
    """
    If a list has only one element, return that element. Otherwise return the whole list.
    """
    try:
        e2 = lista[1]
        return lista
    except IndexError:
        return lista[0]


def pdf(binsize, input, out='no', normalize=True, include_zeros=False, vmin='NA', vmax='NA', start_from='NA',
        closing_bin=False):
    """
    Return the probability density function of "input"
    using linear bins of size "binsize"

    Input format: one column of numbers

    Example:
    ---------
      a, m = 0.5, 1.
      data = np.random.pareto(a, 1000) + m
      xy = pdf(10.0, data)
    """
    # Detect input type:
    if input == sys.stdin:
        # the data come form standard input
        d = [list_check(map(float, l.split())) for l in sys.stdin]
    #         d = [ float(l) for l in sys.stdin if l.strip() ]
    elif isinstance(input, str):
        # the data come from a file
        d = [list_check(map(float, l.split())) for l in open(input, 'r')]
    #         d = [ float(w) for w in open(input,'r') if w.split()]
    else:
        # the data are in a list
        try:
            iterator = iter(input)
            d = list(input)
        except TypeError:
            print("The input is not iterable.")

    bin = 1.0 * binsize
    d.sort()
    lend = len(d)
    hist = []
    if out != 'no' and out != 'stdout': f = open(out, 'wb')

    j = 0
    if not isinstance(start_from, str):
        i = int(start_from / bin) + 1.0 * segno(start_from)
    else:
        i = int(d[j] / bin) + 1.0 * segno(d[j])

    while True:
        cont = 0
        average = 0.0
        if i >= 0:
            ii = i - 1
        else:
            ii = i
        # To include the lower end in the previous bin, substitute "<" with "<="
        while d[j] < bin * (ii + 1):
            cont += 1.0
            average += 1.0
            j += 1
            if j == lend: break
        if cont > 0 or include_zeros == True:
            if normalize == True and i != 0:
                hist += [[bin * (ii) + bin / 2.0, average / (lend * bin)]]
            elif i != 0:
                hist += [[bin * (ii) + bin / 2.0, average / bin]]
        if j == lend: break
        i += 1
    if closing_bin:
        # Add the "closing" bin
        hist += [[hist[-1][0] + bin, 0.0]]
    if out == 'stdout':
        for l in hist:
            print("%s %s" % (l[0], l[1]))
    elif out != 'no':
        for l in hist:
            f.write("%s %s\n" % (l[0], l[1]))
        f.close()
    if out == 'no': return hist


def lbpdf(binsize, input, out='no'):
    """
    Return the probability density function of "input"
    using logarithmic bins of size "binsize"

    Input format: one column of numbers

    Example:
    ---------
      a, m = 0.5, 1.
      data = np.random.pareto(a, 1000) + m
      xy = lbpdf(1.5, data)
    """
    # Detect input type:
    if input == sys.stdin:
        # the data come form standard input
        d = [list_check(map(float, l.split())) for l in sys.stdin]
    #         d = [ float(l) for l in sys.stdin if l.strip() ]
    elif isinstance(input, str):
        # the data come from a file
        d = [list_check(map(float, l.split())) for l in open(input, 'r')]
    #         d = [ float(w) for w in open(input,'r') if w.split()]
    else:
        # the data are in a list
        try:
            iterator = iter(input)
            d = list(input)
        except TypeError:
            print("The input is not iterable.")

    bin = 1.0 * binsize
    d.sort()
    # The following removes elements too close to zero
    while d[0] < 1e-12:
        del (d[0])
    lend = len(d)
    tot = 0
    hist = []

    j = 0
    i = 1.0
    previous = min(d)

    while True:
        cont = 0
        average = 0.0
        next = previous * bin
        # To include the lower end in the previous bin, substitute "<" with "<="
        while d[j] < next:
            cont += 1.0
            average += 1.0
            j += 1
            if j == lend: break
        if cont > 0:
            hist += [[previous + (next - previous) / 2.0, average / (next - previous)]]
            tot += average
        if j == lend: break
        i += 1
        previous = next

    if out != 'no' and out != 'stdout': f = open(out, 'wb')
    if out == 'stdout':
        for x, y in hist:
            print("%s %s" % (x, y / tot))
    elif out != 'no':
        f = open(out, 'wb')
        for x, y in hist:
            f.write("%s %s\n" % (x, y / tot))
        f.close()
    if out == 'no': return [[x, y / tot] for x, y in hist]


class Parameter:
    def __init__(self, value):
        self.value = value

    def set(self, value):
        self.value = value

    def __call__(self):
        return self.value


def LSfit(function, parameters, y, x):
    """
    *** ATTENTION! ***
    *** _x_ and _y_ MUST be NUMPY arrays !!! ***
    *** and use NUMPY FUNCTIONS, e.g. np.exp() and not math.exp() ***

    _function_    ->   Used to calculate the sum of the squares:
                         min   sum( (y - function(x, parameters))**2 )
                       {params}

    _parameters_  ->   List of elements of the Class "Parameter"
    _y_           ->   List of observations:  [ y0, y1, ... ]
    _x_           ->   List of variables:     [ [x0,z0], [x1,z1], ... ]

    Then _function_ must be function of xi=x[0] and zi=x[1]:
        def f(x): return x[0] *  x[1] / mu()

        # Gaussian
            np.exp( -(x-mu())**2.0/sigma()**2.0/2.0)/(2.0*sigma()**2.0*np.pi)**0.5
        # Lognormal
            np.exp( -(np.log(x)-mu())**2.0/sigma()**2.0/2.0)/(2.0*sigma()**2.0*np.pi)**0.5/x

    Example:
        x=[np.random.normal() for i in range(1000)]
        variables,data = map(np.array,zip(*pdf(0.4,x)))

        # giving INITIAL _PARAMETERS_:
        mu     = Parameter(7)
        sigma  = Parameter(3)

        # define your _FUNCTION_:
        def function(x): return np.exp( -(x-mu())**2.0/sigma()**2.0/2.0)/(2.0*sigma()**2.0*np.pi)**0.5

        ######################################################################################
        USA QUESTE FORMULE
        #Gaussian formula
        #np.exp( -(x-mu())**2.0/sigma()**2.0/2.0)/(2.0*np.pi)**0.5/sigma()
        # Lognormal formula
        #np.exp( -(np.log(x)-mu())**2.0/sigma()**2.0/2.0)/(2.0*np.pi)**0.5/x/sigma()
        ######################################################################################


        np.exp( -(x-mu())**2.0/sigma()**2.0/2.0)/(2.0*np.pi)**0.5/sigma()

        # fit! (given that data is an array with the data to fit)
        popt,cov,infodict,mesg,ier,pcov,chi2 = LSfit(function, [mu, sigma], data, variables)
    """
    x = np.array(x)
    y = np.array(y)

    def f(params):
        i = 0
        for p in parameters:
            p.set(params[i])
            i += 1
        return y - function(x)

    p = [param() for param in parameters]
    popt, cov, infodict, mesg, ier = optimize.leastsq(f, p, maxfev=10000,
                                                      full_output=1)  # , warning=True)   #, args=(x, y))

    if (len(y) > len(p)) and cov is not None:
        # s_sq = (f(popt)**2).sum()/(len(y)-len(p))
        s_sq = (infodict['fvec'] ** 2).sum() / (len(y) - len(p))
        pcov = cov * s_sq
    else:
        pcov = float('Inf')

    R2 = 1.0 - (infodict['fvec'] ** 2.0).sum() / standard_dev(y) ** 2.0 / len(y)

    # Detailed Output: p,cov,infodict,mesg,ier,pcov,R2
    return popt, cov, infodict, mesg, ier, pcov, R2


def maximum_likelihood(function, parameters, data, full_output=True, verbose=True):
    """
    function    ->  callable: Distribution from which data are drawn. Args: (parameters, x)
    parameters  ->  np.array: initial parameters
    data        ->  np.array: Data

    Example:

        m=0.5
        v=0.5
        parameters = numpy.array([m,v])

        data = [random.normalvariate(m,v**0.5) for i in range(1000)]

        def function(p,x): return numpy.exp(-(x-p[0])**2.0/2.0/p[1])/(2.0*numpy.pi*p[1])**0.5

        maximum_likelihood(function, parameters, data)


        # # Check that is consistent with Least Squares when "function" is a gaussian:
        # mm=Parameter(0.1)
        # vv=Parameter(0.1)
        # def func(x): return numpy.exp(-(x-mm())**2.0/2.0/vv())/(2.0*numpy.pi*vv())**0.5
        # x,y = zip(*pdf(0.1,data,out='no'))
        # popt,cov,infodict,mesg,ier,pcov,chi2 = LSfit(func, [mm,vv], y, x)
        # popt
        #
        # # And with the exact M-L values:
        # mm = sum(data)/len(data)
        # vv = standard_dev(data)
        # mm, vv**2.0
    """

    def MLprod(p, data, function):
        return -np.sum(np.array([np.log(function(p, x)) for x in data]))

    return optimize.fmin(MLprod, parameters, args=(data, function), full_output=full_output, disp=verbose)


INTERRUPTION = 5
FOUL = 2
OFFSIDE = 6
DUEL = 1
SHOT = 10
SAVE_ATTEMPT = 91
REFLEXES = 90
TOUCH = 72
DANGEROUS_BALL_LOST = 2001
MISSED_BALL = 1302
PASS = 8
PENALTY = 35
ACCURATE_PASS = 1801

END_OF_GAME_EVENT = {
    u'eventName': -1,
    u'eventSec': 7200,
    u'id': -1,
    u'matchId': -1,
    u'matchPeriod': u'END',
    u'playerId': -1,
    u'positions': [],
    u'subEventName': -1,
    u'tags': [],
    u'teamId': -1
}

START_OF_GAME_EVENT = {
    u'eventName': -2,
    u'eventSec': 0,
    u'id': -2,
    u'matchId': -2,
    u'matchPeriod': u'START',
    u'playerId': -2,
    u'positions': [],
    u'subEventName': -2,
    u'tags': [],
    u'teamId': -2
}

tags_names_df = pd.read_csv('C:\\Users\\Nathaniel L\\Desktop\\Data\\tags2name.csv')
event_names_df = pd.read_csv('C:\\Users\\Nathaniel L\\Desktop\\Data\\eventid2name.csv')
event_names_df.loc[event_names_df.index[-1] + 1] = [-1, -1, 'End of game', 'End of game']


def get_event_name(event):
    event_name = ''
    try:
        if event['subEventName'] != '':
            event_name = event_names_df[(event_names_df.event == event['eventName']) & (
                        event_names_df.subevent == event['subEventName'])].subevent_label.values[0]
        else:
            event_name = event_names_df[event_names_df.event == event['eventName']].event_label.values[0]
    except TypeError:
        # print event
        pass

    return event_name


def get_tag_list(event):
    return [tags_names_df[tags_names_df.Tag == tag['id']].Description.values[0] for tag in event['tags']]


def pre_process(events):
    """
    Duels appear in pairs in the streamflow: one event is by a team and the other by
    the opposing team. This can create
    """
    filtered_events, index, prev_event = [], 0, {'teamId': -1}

    while index < len(events) - 1:
        current_event, next_event = events_match[index], events_match[index + 1]

        # if it is a duel
        if current_event['eventName'] == DUEL:

            if current_event['teamId'] == prev_event['teamId']:
                filtered_events.append(current_event)
            else:
                filtered_events.append(next_event)
            index += 1

        else:
            # if it is not a duel, just add the event to the list
            filtered_events.append(current_event)
            prev_event = current_event

        index += 1
    return filtered_events


def is_interruption(event, current_half):
    """
    Verify whether or not an event is a game interruption. A game interruption can be due to
    a ball our of the field, a whistle by the referee, a fouls, an offside, the end of the
    first half or the end of the game.

    Parameters
    ----------
    event: dict
        a dictionary describing the event

    current_half: str
        the current half of the match (1H = first half, 2H == second half)

    Returns
    -------
    True is the event is an interruption
    False otherwise
    """
    event_id, match_period = event['eventName'], event['matchPeriod']
    if event_id in [INTERRUPTION, FOUL, OFFSIDE] or match_period != current_half or event_id == -1:
        return True
    return False


def is_pass(event):
    return event['eventName'] == PASS


def is_accurate_pass(event):
    return ACCURATE_PASS in [tag['id'] for tag in event['tags']]


def is_shot(event):
    """
    Verify whether or not the event is a shot. Sometimes, a play action can continue
    after a shot if the team gains again the ball. We account for this case by looking
    at the next events of the game.

    Parameters
    ----------
    event: dict
        a dictionary describing the event

    Returns
    -------
    True is the event is a shot
    False otherwise
    """
    event_id = event['eventName']
    return event_id == 10


def is_save_attempt(event):
    return event['subEventName'] == SAVE_ATTEMPT


def is_reflexes(event):
    return event['subEventName'] == REFLEXES


def is_touch(event):
    return event['subEventName'] == TOUCH


def is_duel(event):
    return event['eventName'] == DUEL


def is_ball_lost(event, previous_event):
    tags = get_tag_list(event)
    # if DANGEROUS_BALL_LOST in tags or MISSED_BALL in tags:
    #    return True
    # if event['eventName'] == PASS:
    #    if 'Not accurate' in tags:
    #        return True
    if event['teamId'] != previous_event['teamId'] and previous_event['teamId'] != -2 and event['eventName'] != 1:
        return True

    return False


def is_penalty(event):
    return event['subEventName'] == PENALTY


def get_play_actions(db, match_id, verbose=False):
    """
    Given a list of events occuring during a game, it splits the events
    into play actions using the following principle:

    - an action begins when a team gains ball possession
    - an action ends if one of three cases occurs:
    -- there is interruption of the match, due to: 1) end of first half or match; 2) ball
    out of the field 3) offside 4) foul

    """
    try:

        events_match = []
        for nation in nations:
            for ev in events[nation]:
                if ev['matchId'] == match_id:
                    events_match.append(ev)

        half_offset = {'2H': max([x['eventSec'] for x in events_match if x['matchPeriod'] == '1H']),
                       '1H': 0}
        events_match = sorted(events_match, key=lambda x: x['eventSec'] + half_offset[x['matchPeriod']])
        ## add a fake event representing the start and end of the game
        events_match.insert(0, START_OF_GAME_EVENT)
        events_match.append(END_OF_GAME_EVENT)

        play_actions = []

        time, index, current_action, current_half = 0.0, 1, [], '1H'
        previous_event = events_match[0]
        while index < len(events_match) - 2:

            current_event = events_match[index]

            # if the action stops by an game interruption
            if is_interruption(current_event, current_half):
                current_action.append(current_event)
                play_actions.append(('interruption', current_action))
                current_action = []

            elif is_penalty(current_event):
                next_event = events_match[index + 1]

                if is_save_attempt(next_event) or is_reflexes(next_event):
                    index += 1
                    current_action.append(current_event)
                    current_action.append(next_event)
                    play_actions.append(('penalty', current_action))
                    current_action = []
                else:
                    current_action.append(current_event)

            elif is_shot(current_event):
                next_event = events_match[index + 1]

                if is_interruption(next_event, current_half):
                    index += 1
                    current_action.append(current_event)
                    current_action.append(next_event)
                    play_actions.append(('shot', current_action))
                    current_action = []

                ## IF THERE IS A SAVE ATTEMPT OR REFLEXES; GO TOGETHER
                elif is_save_attempt(next_event) or is_reflexes(next_event):
                    index += 1
                    current_action.append(current_event)
                    current_action.append(next_event)
                    play_actions.append(('shot', current_action))
                    current_action = []

                else:
                    current_action.append(current_event)
                    play_actions.append(('shot', current_action))
                    current_action = []

            elif is_ball_lost(current_event, previous_event):

                current_action.append(current_event)
                play_actions.append(('ball lost', current_action))
                current_action = [current_event]

            else:
                current_action.append(current_event)

            time = current_event['eventSec']
            current_half = current_event['matchPeriod']
            index += 1

            if not is_duel(current_event):
                previous_event = current_event

        events_match.remove(START_OF_GAME_EVENT)
        events_match.remove(END_OF_GAME_EVENT)

        return play_actions
    except TypeError:
        return []


def get_datadriven_weight(position, normalize=True):
    """
    Get the probability of scoring a goal given the position of the field where
    the event is generated.

    Parameters
    ----------
    position: tuple
        the x,y coordinates of the event

    normalize: boolean
        if True normalize the weights
    """
    weights = np.array([[0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 2.00000000e+00, 2.00000000e+00,
                         0.00000000e+00],
                        [0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 8.00000000e+00, 1.10000000e+01,
                         1.00000000e+00],
                        [0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         4.00000000e+00, 4.00000000e+01, 1.28000000e+02,
                         7.00000000e+01],
                        [0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         1.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         9.00000000e+00, 1.01000000e+02, 4.95000000e+02,
                         4.83000000e+02],
                        [0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         6.00000000e+00, 9.80000000e+01, 5.60000000e+02,
                         1.12000000e+03],
                        [0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         1.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         8.00000000e+00, 9.30000000e+01, 5.51000000e+02,
                         7.82000000e+02],
                        [0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         3.00000000e+00, 6.70000000e+01, 3.00000000e+02,
                         2.30000000e+02],
                        [0.00000000e+00, 1.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         1.00000000e+00, 1.30000000e+01, 3.20000000e+01,
                         1.10000000e+01],
                        [0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         1.00000000e+00, 2.00000000e+00, 2.00000000e+00,
                         2.00000000e+00],
                        [1.00000000e+00, 0.00000000e+00, 0.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 1.00000000e+00,
                         0.00000000e+00, 0.00000000e+00, 1.00000000e+00,
                         0.00000000e+00]])

    x, y = position

    if x == 100.0:
        x = 99.9

    if y == 100.0:
        y = 99.9

    w = weights[int(y / 10)][int(x / 10)]

    if normalize:  # normalize the weights
        w = w / np.sum(weights)
    return w


def get_weight(position):
    """
    Get the probability of scoring a goal given the position of the field where
    the event is generated.

    Parameters
    ----------
    position: tuple
        the x,y coordinates of the event
    """
    x, y = position

    # 0.01
    if x >= 65 and x <= 75:
        return 0.01

    # 0.5
    if (x > 75 and x <= 85) and (y >= 15 and y <= 85):
        return 0.5
    if x > 85 and (y >= 15 and y <= 25) or (y >= 75 and y <= 85):
        return 0.5

    # 0.02
    if x > 75 and (y <= 15 or y >= 85):
        return 0.02

    # 1.0
    if x > 85 and (y >= 40 and y <= 60):
        return 1.0

    # 0.8
    if x > 85 and (y >= 25 and y <= 40 or y >= 60 and y <= 85):
        return 0.8

    return 0.0


match_id = 2576263
a_match = []
for nation in nations:
    for ev in events[nation]:
        if ev['matchId'] == match_id:
            a_match.append(ev)

df_a_match = pd.DataFrame(a_match)

for nation in nations:
    for match in matches[nation]:
        if match['wyId'] == 2576263:
            match_f = match

print(match_f['label'])

match_id = 2576263

list_invasion, list_acceleration = get_invasion_index(a_match,match_id,lst=True)




s1 = alt.selection_interval(encodings=["x"], empty=True)

window_size = 220
colorCondition1 = alt.condition(s1, alt.Color('team:N', legend=None), alt.value("gray"))

# Create a combined dataframe and normalize the time
combined_data_acceleration = []
for i, color, label in zip(list(list_acceleration), ['darkred', 'k'], ['AS Roma', 'ACF Fiorentina']):
    df_acceleration = pd.DataFrame(list_acceleration[i], columns=['time', 'acceleration'])
    df_acceleration['time'] = df_acceleration['time'] / 60
    df_acceleration['team'] = label
    print(label, df_acceleration['acceleration'].mean(), df_acceleration['acceleration'].std())
    combined_data_acceleration.append(df_acceleration)

df_combined_acceleration = pd.concat(combined_data_acceleration)

# Create a rolling average
df_combined_acceleration['rolling_avg'] = df_combined_acceleration.groupby('team')['acceleration'].transform(lambda x: x.rolling(window_size, min_periods=1).mean())

# Line Graph
chart_acceleration = alt.Chart(df_combined_acceleration).mark_line().encode(
    x=alt.X('time', title='Time (in minutes)'),
    y=alt.Y('rolling_avg', axis=alt.Axis(title='Acceleration Index', titleFontSize=25, labelFontSize=18, grid=True)),
    color=colorCondition1,
    strokeDash='team',
).properties(
    width=700,
    height=350,
    title='ACCELERATION INDEX'
)

# Vertical lines and text annotations
half_time_line = alt.Chart(pd.DataFrame({'time': [45.8]})).mark_rule(color='red', strokeWidth=2).encode(x='time')
half_time_text = alt.Chart(pd.DataFrame({'time': [45.8], 'text': ['half time']})).mark_text(
    align='left', baseline='middle', fontSize=15, angle=90, dx=5, color='red'
).encode(x='time', text='text')

goal_line_1 = alt.Chart(pd.DataFrame({'time': [7]})).mark_rule(color='rebeccapurple', strokeWidth=2).encode(x='time')
goal_text_1 = alt.Chart(pd.DataFrame({'time': [6], 'text': ['goal']})).mark_text(
    align='left', baseline='middle', fontSize=15, angle=90, dx=5, color='rebeccapurple'
).encode(x='time', text='text')

goal_line_2 = alt.Chart(pd.DataFrame({'time': [39]})).mark_rule(color='rebeccapurple', strokeWidth=2).encode(x='time')
goal_text_2 = alt.Chart(pd.DataFrame({'time': [38], 'text': ['goal']})).mark_text(
    align='left', baseline='middle', fontSize=15, angle=90, dx=5, color='rebeccapurple'
).encode(x='time', text='text')

c2 = chart_acceleration.add_params(s1).encode(
    color=colorCondition1
).properties(
    title={'text': match_f['label'], 'fontSize': 35}
)

# Bar Plot
rolling_avg = df_combined_acceleration.groupby("team")["rolling_avg"].mean().reset_index()
bars = alt.Chart(df_combined_acceleration).mark_bar(opacity=0.6, height=15).encode(
    y=alt.Y("team:N", title="Team"),
    x=alt.X("mean(rolling_avg):Q", title='Acceleration Index', axis=alt.Axis(grid=False)),
    color=alt.Color("team:N")
)


c3 = bars.add_params(s1).transform_filter(s1)

print(c2 & c3)