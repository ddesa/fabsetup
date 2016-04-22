# Own F-Droid Repository

With an [own](https://f-droid.org/wiki/page/Setup_an_FDroid_App_Repo "own froid
repo") F-Droid Repository (f-droid repo) hosted by yourself you can provide any
Android app you want and easily install them on your Android device.

Motivation: If you don't want to have any Google Apps on your Android device
you could use [Cyanogenmod](http://www.cyanogenmod.org/ "www.cyanogenmod.org")
without the [gapps package](https://wiki.cyanogenmod.org/w/Google_Apps)
installed.  As an alternative to Google's play-store you can then use
[F-Droid](https://f-droid.org/) in oder to install Android apps.  But probably
you also want to install apps, which are not available in F-Droid's main
repository.

## Install and set up your f-droid repo

Scenario: You have a shell with sudo access on an internet hosting machine
(server) running (ubuntu) linux.

On your local pc open a shell, go to the fabsetup dir and run the task
`setup.service.fdroid`. This will happen on your server:
* install and enable nginx service
  * deinstall and disable apache service
* install fdroidserver from the personal package archive
  ([ppa](https://wiki.ubuntuusers.de/Launchpad/PPA/)) of the
  [guardianproject](https://guardianproject.info/)
* Create a f-droid repo
* Set up the f-droid repo as a https website served by the nginx service

  ```sh
  cd ~/repos/fabsetup
  fab setup.service.fdroid -H <server>
  ```

## Create webserver certificate for your f-droid repo via letsencrypt

In your custom fabsetup repo in the `config.py` file uncomment the line
  ```python
  #        'fdroid.{{hostname}}',
  ```
and replace `{{hostname}}` by the domain of your internet host, e.g.
  ```python
  domain_groups = [
      [
          'fdroid.example.com',
	  # ...
      ],
      # ...
  ]
  ```

Now create a certificate using task `setup.server_letsencrypt`:
  ```sh
  fab setup.server_letsencrypt -H <server>
  ```

Save the changes of your custom fabsetup repo, e.g.
  ```sh
  cd ~/repos/fabsetup/fabsetup_custom
  git commit -am 'add domain fdroid.example.com for letsencrypt certificates'
  ```

Your repo is now available at this URL: `https://fdroid.<your_domain>/repo`

## Add android apps manually

Every time when task `setup.service.fdroid` is executed it looks for .apk files
placed at `~/sites/fdroid.<your_domain>/apks/` and copies them to the repo dir.

To add an android app to your f-droid repo, put the .apk file in the apks dir
and run the task `setup.service.fdroid` again, e.g.
  ```sh
  scp  path/to/your/app.apk  example.com:~/sites/fdroid.example.com/apks/

  cd ~/repos/fabsetup
  fab setup.service.fdroid
  ```

Hint: If you host non-free apps with your f-droid repo it must not be publicly
available.
