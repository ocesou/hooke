#!/usr/bin/env python

'''
Input check routines.

Copyright (C) 2008 Alberto Gomez-Casado (University of Twente).

This program is released under the GNU General Public License version 2.
'''

def alphainput (message, default, repeat, valid):
    '''
    message: prompt for the user
    default: return value if user input was not correct (and repeat=0)
    repeat: keeps asking user till it gets a valid input
    valid: list of allowed answers, empty list for "anything"
    ''' 
    if default and not repeat:
        print 'Press [enter] for default: ('+str(default)+')'
    reply=raw_input(message)
    if len(valid)>0:
        if reply in valid: 
            return reply
        else:
            if repeat==1:
                while reply not in valid:
                    reply=raw_input('You should enter any of these: '+ str(valid) +'\n'+ message)
                return reply
            else:
                return default
    else:
        if len(reply)>0:
            return reply
        else:
            if not repeat:
                return default
            else:
                while len(reply)==0:
                    print 'Try again'
                    reply=raw_input(message)
                return reply

                    

def checkalphainput (test, default, valid):
    #useful when input was taken form command args
    if len(valid)>0:
        if test in valid: 
            return test
        else:
            return default
    else:
        #TODO: raise exception?
        if len(test)>0:
            return test
        else:
            return default


def numinput(message, default, repeat, limits):
    '''
    message: prompt for the user
    default: return value if user input was not correct (and repeat=0)
    repeat: keeps asking user till it gets a valid input
    limits: pair of values, input is checked to be between them, empty list for "any number"
    ''' 
    if default and not repeat:
        print 'Enter for default: '+str(default)
    reply=raw_input(message)
    if reply:
        reply=int(reply)
    if len(limits)==2:
        high=int(limits.pop())
        low=int(limits.pop())
        if reply>=low and reply <= high:
            return reply
        else:
            if repeat==1:
                while reply<low or reply>high :
                    reply=raw_input('You should enter values between: '+ str(low)+' and '+str(high) +'\n'+ message)
                    if reply:
                        reply=int(reply)
                return reply
            else:
                return default
    else:
        if len(reply)>0:
            return int(reply)
        else:
            if not repeat:
                return default
            else:
                while len(reply)==0:
                    print 'Try again'
                    reply=raw_input(message)
                return reply

def checknuminput(test,default,limits):
    #useful when input was taken from command args
    if len(limits)==2:
        high=int(limits.pop())
        low=int(limits.pop())
        if test>=low and test <= high:
            return int(test)
        else:
            return default
    else:
        if len(test)>0:
            return int(test)
        else:
            return default

