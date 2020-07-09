#!/usr/bin/env python3

import sys
from os import path, getenv, remove, chmod, environ
from shutil import copy
import datetime
error = False

try:
    import boto3
except:
    print("\033[91mPlease install boto3\033[0m")
    error = True
try:
    import configparser
except:
    print("\033[91mPlease install configparser\033[0m")
    error = True
try:
    import argparse
except:
    print("\033[91mPlease install argparse\033[0m")
    error = True
try:
    from dateutil.tz import tzutc
except:
    print("\033[91mPlease install python-dateutil\033[0m")
    error = True

if error:
    raise Exception("Required modules are missing")

homedir=getenv("HOME")
awscreds=homedir + '/.aws/credentials'

def parse_arguments():
    parser = argparse.ArgumentParser(description="Get temporary awscli credentials with MFA")
    parser.add_argument('-p','--profile', nargs='?', help='Which AWS profile do you want to use for deploying (defaults to "default")')
    parser.add_argument('-o','--otp', nargs='?', help='OTP token')
    parser.add_argument('-c','--credentials', nargs='?', help='AWS credentials configuration file', default=awscreds)
    parser.add_argument('-n','--name', nargs='?', help='Name for profile to use for temporary credentials, (defaults to <profile>-mfa e.g. default-mfa)')
    return parser.parse_args()

def parse_config(awscreds):
    config = configparser.ConfigParser()
    config.read(awscreds)
    return config

def get_temporary_credentials(profile,token):
    session = boto3.session.Session(profile_name=profile)
    sts = session.client('sts')
    iam = session.client('iam')
    username = sts.get_caller_identity().get('Arn').split('/')[1]
    mfa_devices = iam.list_mfa_devices(UserName=username)
    if len(mfa_devices['MFADevices']) < 1:
        print("User {} doesn't seem to have any MFA devices configured".format(username))
        sys.exit(1)
    if len(mfa_devices['MFADevices']) > 1:
        print("There are more than 1 MFA devices available, this script currently supports situations where there are only one available")
        sys.exit(1)
    else:
        mfa_device_arn = (mfa_devices['MFADevices'][0]['SerialNumber'])
        session_credentials = sts.get_session_token(SerialNumber=mfa_device_arn,TokenCode=token)
        return session_credentials

def add_temporary_profile(config,temp_profile,session_credentials):
    if not temp_profile in config:
        config.add_section(temp_profile)
    config.set(temp_profile,"aws_access_key_id",session_credentials['Credentials']['AccessKeyId'])
    config.set(temp_profile,"aws_secret_access_key",session_credentials['Credentials']['SecretAccessKey'])
    config.set(temp_profile,"aws_session_token", session_credentials['Credentials']['SessionToken'])
    config.set(temp_profile,"aws_session_expiration", session_credentials['Credentials']['Expiration'].strftime('%Y-%m-%d %H:%M:%S%z'))
    return config

def write_config(config,awscreds):

    if path.isfile(awscreds):
        bakfile=awscreds + ".bak." + datetime.datetime.now().isoformat()
        print("Creating backup of " + awscreds + " to " + bakfile)
        copy (awscreds,bakfile)

    with open(awscreds,'w') as credentials:
        config.write(credentials)
        chmod(awscreds, 0o600)

def main():
    arguments = parse_arguments()
    awscreds = arguments.credentials
    token = arguments.otp
    temp_profile = arguments.name
    profile = arguments.profile

    if not profile:
        profile = environ.get('AWS_PROFILE')

    if not profile:
        profile = 'default'

    if not temp_profile:
        temp_profile = profile + '-mfa'

    config = parse_config(awscreds)
    if temp_profile in config:
        if config[temp_profile]['aws_session_expiration']:
            now = datetime.datetime.utcnow().replace(tzinfo=tzutc())
            expire_time = datetime.datetime.strptime(config[temp_profile]['aws_session_expiration'],'%Y-%m-%d %H:%M:%S%z')
            if expire_time > now:
                print("No need to refresh yet, {} is still valid until {}".format(temp_profile,expire_time))
                return

    if not token:
        token = input("Enter your OTP code for profile {}: ".format(profile))
    
    session_credentials = get_temporary_credentials(profile,token)
    new_config = add_temporary_profile(config,temp_profile,session_credentials)
    write_config(config,awscreds)
    print("Added/refreshed {}".format(temp_profile))

if __name__ == '__main__':

    main()


