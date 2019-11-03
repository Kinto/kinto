param (
	[System.IO.FileInfo]	$ExternalDotEnv = (Convert-Path '.env'),
	[Hashtable] $DotEnvConfig = @{},
	[String]	$RequirementsFile = 'requirements.txt',
	[String]	$KINTO_INI = 'kinto\config\kinto.ini',
	[Int32]		$Port = 8888,
	[Switch]	$Help,
	[Switch]	$Install,
	[Switch]	$Setup,
	[Switch]	$Run,
	[Switch]	$Test
)

if($Install -OR $Setup -OR $Run -OR $Test){<#Interpre rest of this file right after the condition block over here.#>
} elseif($Help){ Get-Help Kinto-Help -Full | more }
else { Get-Help -Example | more}

if(($ExternalDotEnv.Mode[0..1] -join '') -eq 'd-'){
	ls $ExternalDotEnv -Recurse -Attribute "!d" | cat | %{$e=$_.Split("=");[Environment]::SetEnvironmentVariable($e[0],$e[1])}
} elseif (($ExternalDotEnv.Mode[0..1] -join '') -eq '-a') {cat $ExternalDotEnv | %{$e=$_.Split("=");[Environment]::SetEnvironmentVariable($e[0],$e[1])}}
else{
	<# Can be thrown due to force user to set the environments by means of either $DotEnvConfig or $ExternalDotEnv #>
}

<# It overwrite on environment variables if it's been set #>
if ($DotEnvConfig -ne $null){
	$DotEnvConfig.Keys | %{[Environment]::SetEnvironmentVariable("$_","$DotEnvConfig[$_]")}
}
# Write-Output (ls env:)

function ValidateVersions {
	$VSCMD_VER = ([System.Environment]::GetEnvironmentVariable("VSCMD_VER"))
	if($VSCMD_VER -lt '14.0') {throw "You need to install MSBuild 14.0+"}
	$env = $env:Path.Split(";");
	<# .DESCRIPTION
	    It's important to use for instead of foreach because it has to be synchronised and first match should be taken an account.#>
	for($i=0; $i -lt $env.Length; $i++){
		if((Test-Path (Join-Path $env[$i] "python.exe")) -OR (Test-Path (Join-Path $env[$i] "python3*.exe"))) {
			$pyexe = "python"
			iex "$pyexe -c `"import sys; print('%s.%s'%(sys.version_info.major,sys.version_info.minor))`"" -OutVariable pyv | Out-Null
			if ($pyv -match "^3\.[6-9]$"){return $true}
		}
	}
	throw "You need to install python 3.6+"
}

function SetAndGet-PIP {
	iex "$PyEXE -c 'import pip; print(pip.__spec__.name)'" -OutVariable pip | Out-Null
	if(-not ($pip -match "pip[3]?")){
		if(-NOT(Test-Path $env:TEMP)){$env:TEMP="tmp"}
		try {
			Write-Warning "Downloading get-pip from `"https://bootstrap.pypa.io/get-pip.py`" to `t`"($($env:TEMP))`""
			iex 'curl -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$($env:TEMP)\get-pip.py" -Credential $env:USERNAME'
			iex "$PyEXE $($env:TEMP)\get-pip.py"
			return 'pip'
		} catch{<#TO DO#>
			Write-Error $_
			throw "To run the application you need pip module. You can download get-pip via `"https://bootstrap.pypa.io/get-pip.py`" manualy."
		}
	}
	return $pip
}

function Get-Prerequisite {
	$inf = @{'VSCMD_VER'=$null;'PYTHON_VER'=$null;'PyEXE'=$null}
	$VSCMD_VER = ([System.Environment]::GetEnvironmentVariable("VSCMD_VER"))
	$env = $env:Path.Split(";");
	<# .DESCRIPTION
	    It's important to use for instead of foreach because it has to be synchronised and first match should be taken an account.#>
	for($i=0; $i -lt $env.Length; $i++){
		if((Test-Path (Join-Path $env[$i] "python.exe")) -OR (Test-Path (Join-Path $env[$i] "python3*.exe"))) {
			$pyroot = $env[$i]
			$pyexe = "python"
			$pycandidate = (Get-ChildItem "$pyroot\*python*exe").FullName
			iex "$pyexe -c `"import sys; print('%s.%s'%(sys.version_info.major,sys.version_info.minor))`"" -OutVariable pyv | Out-Null
			if ($pyv -match "^[23]\.[6-9]$"){$PYTHON_VER=$pyv}
			for ($j=0; $j -lt $pycandidate.Length; $j++){
				if($pycandidate[$j] -match ".*[\\\/]+python[\.\-\d]+exe$"){$pyexe=$pycandidate[$j];break}
			}
			$inf = @{'VSCMD_VER'=$VSCMD_VER;'PYTHON_VER'=$PYTHON_VER|%{$_};'PyEXE'=$pyexe}
			$t = if($VSCMD_VER -ge '14.0'){1}else{0}
			$t += if($pyv -ge '3.6'){1}else{0}
			if ($t -eq 2) {
				iex "$PyEXE -c 'import pip; print(pip.__spec__.name)'" -OutVariable pip | Out-Null
				if(-not ($pip -match "pip[3]?")){
					if(-NOT(Test-Path $env:TEMP)){$env:TEMP="tmp"}
					try {
						Write-Warning "Downloading get-pip from `"https://bootstrap.pypa.io/get-pip.py`" to `t`"($($env:TEMP))`""
						# iex 'curl -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$($env:TEMP)\get-pip.py" -Credential $env:USERNAME'
						# iex "$PyEXE $($env:TEMP)\get-pip.py"
						$pip = 'pip'
					} catch{<#TO DO#>
						Write-Error $_
						throw "To run the application you need pip module. You can download get-pip via `"https://bootstrap.pypa.io/get-pip.py`" manualy."
					}
				}
				$pip | %{$inf.Add('pip', $_)}
			} else {Write-Host "t:($t)" -ForegroundColor 'yellow'}
		}
	}
	if($inf['PYTHON_VER'] -lt '3.6') {throw "You need to install python 3.6+"}
	if($inf['VSCMD_VER'] -lt '14.0') {throw "You need to install MSBuild 14.0+"}
	Sleep 1
	$inf
}

<#
	.SYNOPSIS
	Running Kinto Application
	
	.DESCRIPTION
	It's gonna set and validate the required environment variables.
	If all prerequisites are satisfied it applies options including Install, Setup, Run, or Test.

	.PARAMETER DotEnvConfig
	The `Hashtable` environment key-value pairs required by Kinto application.

	.PARAMETER ExternalDotEnv
		TYPE System.IO.FileInfo
		DESCRIPTION If DotEnvConfig isn't set it's looking for config file in which contains key-value pairs.
		The default value is .env in which identifies either specific file or a root folder to be explored recursively.
	
	.PARAMETER RequirementsFile
	The file with required packages to run Kinto application.
	
	.PARAMETER KINTO_INI
	Specifying the KINTO_INI file. This file has to be in a valid format with all header quoted between brackets [].
	Line after header contain key-value pairs each of whihc line can be commented by semicolone at its first column. 
	
	.PARAMETER Port
	Identifying the port number; default value is 8888
	
	.PARAMETER Help
	Show help messages including synopsys and examples.
	
	.PARAMETER Install
	If the Install flag is on, it runs the "pip install -r $RequirementsFile".
	
	.PARAMETER Setup
	If the Install flag is on, it runs the `setup.py`.
	
	.PARAMETER Run
	If it's applied without Install flag it runs the Kinto application without checking the requirements and chnages the working directory
	to the build-root if it exists unless it remains in current working directory and run kinto.exe with its options specified in doc.
	
	.PARAMETER Test
	Test the Kinto application by executing `pytest` that is necessarily to be listed in requirements file.
	
	.OUTPUTS
	System.String in seperate line of standard output and System.Process in user kernel to run the application.
	
	.EXAMPLE
	C:\Kinto> .\kinto.ps1
	Print a short list of examples
	
	.EXAMPLE
	C:\Kinto> .\kinto.ps1 -Help
	Print a full list of arguments and examples

	.EXAMPLE
	C:\Kinto> .\kinto.ps1 -Install -Run
	Installing the requirements from $RequirementsFile, then it runs the Kinto application.

	.EXAMPLE
	C:\Kinto> .\kinto.ps1 -Setup -Run
	Setting up the application and then run the Kinto application.

	.EXAMPLE
	C:\Kinto> $strConf = @"
		KINTO_CACHE_BACKEND=kinto.core.cache.memcached
		KINTO_CACHE_HOSTS=cache:11211 cache:11212
		KINTO_STORAGE_BACKEND=kinto.core.storage.postgresql
		KINTO_STORAGE_URL=postgresql://postgres:postgres@db/postgres
		KINTO_PERMISSION_BACKEND=kinto.core.permission.postgresql
		KINTO_PERMISSION_URL=postgresql://postgres:postgres@db/postgres
	"@
	C:\Kinto> $conf = ConvertFrom-StringData $strConf
	C:\Kinto> .\kinto.ps1 -DotEnvConfig $conf -Run
	It sets the environment variable from the DotEnvConfig Hashtable and then run the Kinto application.

	.EXAMPLE
	C:\FlackApp> .\kinto.ps1 -ExternalDotEnv .\.env -RequirementsFile requirements.txt -Setup -Run
	It sets the environment variables from .\.env external link if its attribute is a file unless it'll be considered as a folder
	and lists all files within it recursively so that each file can contain multiple key-value pairs. 
	Next, it sets up the project by running `python3 .\setup.py install`. Finally, it runs the Kinto application.

	.LINK
	https://github.com/Kinto/kinto
	https://github.com/kaloneh/kinto

	.LINK
	Set-ExecutionPolicy
	Invoke-Command
	
#>
function Kinto-Help {
	# TO DO
	<#
		.FORWARDHELPTARGETNAME Get-Help
		.FORWARDHELPCATEGORY Cmdlet
	#>
	[CmdletBinding(DefaultParameterSetName='AllUsersView')]
	param (
		[Hashtable] $DotEnvConfig = @{},
		[System.IO.FileInfo] $ExternalDotEnv = '.env\web',
		[string] $RequirementsFile = 'requirements.txt',
		[String]	$KINTO_INI = '',
		[Int32]		$Port = 8888,
		[Switch]	$Help,
		[Switch]	$Install,
		[Switch]	$Setup,
		[Switch]	$Run,
		[Switch]	$Test
	)
}

function Create-IniTemplate{
	param ($From, $To="kinto\config\kinto.ini")
	if(Test-Path $From){
		$template = (cat $From -Encoding 'Ascii')
	} else {
		$template = "# Created at Wed, 30 Oct 2019 02:54:09 +0000`n# Using Kinto version 1313.7.0.dev0`n# Full options list for .ini file`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html`n`n`n`[server:main`]`nuse = egg:waitress#main`nhost = 0.0.0.0`nport = %(http_port)s`n`n`n`[app:main`]`nuse = egg:kinto`n`n# Feature settings`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#feature-settings`n#`n# kinto.readonly = false`n# kinto.batch_max_requests = 25`n# kinto.paginate_by =`n# Experimental JSON-schema on collection`n# kinto.experimental_collection_schema_validation = false`n#`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#activating-the-permissions-endpoint`n# kinto.experimental_permissions_endpoint = false`n#`n# kinto.trailing_slash_redirect_enabled = true`n# kinto.heartbeat_timeout_seconds = 10`n`n# Plugins`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#plugins`n# https://github.com/uralbash/awesome-pyramid`nkinto.includes = kinto.plugins.default_bucket`n                 kinto.plugins.admin`n                 kinto.plugins.accounts`n#                kinto.plugins.history`n#                kinto.plugins.quotas`n`n# Backends`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#storage`n#`nkinto.storage_backend = kinto.core.storage.memory`nkinto.storage_url =`n# kinto.storage_max_fetch_size = 10000`n# kinto.storage_pool_size = 25`n# kinto.storage_max_overflow = 5`n# kinto.storage_pool_recycle = -1`n# kinto.storage_pool_timeout = 30`n# kinto.storage_max_backlog = -1`n`n# Cache`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#cache`n#`nkinto.cache_backend = kinto.core.cache.memory`nkinto.cache_url =`n# kinto.cache_prefix =`n# kinto.cache_max_size_bytes = 524288`n# kinto.cache_pool_size = 25`n# kinto.cache_max_overflow = 5`n# kinto.cache_pool_recycle = -1`n# kinto.cache_pool_timeout = 30`n# kinto.cache_max_backlog = -1`n`n# kinto.cache_backend = kinto.core.cache.memcached`n# kinto.cache_hosts = 127.0.0.1:11211`n`n# Permissions.`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#permissions`n#`nkinto.permission_backend = kinto.core.permission.memory`nkinto.permission_url =`n# kinto.permission_pool_size = 25`n# kinto.permission_max_overflow = 5`n# kinto.permission_pool_recycle = 1`n# kinto.permission_pool_timeout = 30`n# kinto.permission_max_backlog - 1`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#bypass-permissions-with-configuration`n# kinto.bucket_create_principals = system.Authenticated`n`n# Authentication`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#authentication`n#`nkinto.userid_hmac_secret = b61e418fda25f50085afefeac728fecba726ac6321f8e86e041d014b0abbd5b4`nmultiauth.policies = account`n# Any pyramid multiauth setting can be specified for custom authentication`n# https://github.com/uralbash/awesome-pyramid#authentication`n#`n# Accounts API configuration`n#`n# Enable built-in plugin.`n# Set ``kinto.includes`` to ``kinto.plugins.accounts```n# Enable authenticated policy.`n# Set ``multiauth.policies`` to ``account```nmultiauth.policy.account.use = kinto.plugins.accounts.AccountsPolicy`n# Allow anyone to create accounts.`nkinto.account_create_principals = system.Everyone`n# Set user `'account:admin`' as the administrator.`nkinto.account_write_principals = account:admin`n# Allow administrators to create buckets`nkinto.bucket_create_principals = account:admin`n# Enable the `"account_validation`" option.`n# kinto.account_validation = true`n# Set the sender for the validation email.`n# kinto.account_validation.email_sender = `"admin@example.com`"`n# Set the regular expression used to validate a proper email address.`n# kinto.account_validation.email_regexp = `"^`[a-zA-Z0-9_.+-`]+@`[a-zA-Z0-9-`]+\\.`[a-zA-Z0-9-.`]+`$`"`n`n# Mail configuration (needed for the account validation option), see https://docs.pylonsproject.org/projects/pyramid_mailer/en/latest/#configuration`n# mail.host = localhost`n# mail.port = 25`n# mail.username = someusername`n# mail.password = somepassword`n`n# Notifications`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#notifications`n#`n# Configuration example:`n# kinto.event_listeners = redis`n# kinto.event_listeners.redis.use = kinto_redis.listeners`n# kinto.event_listeners.redis.url = redis://localhost:6379/0`n# kinto.event_listeners.redis.pool_size = 5`n# kinto.event_listeners.redis.listname = queue`n# kinto.event_listeners.redis.actions = create`n# kinto.event_listeners.redis.resources = bucket collection`n`n# Production settings`n#`n# https://kinto.readthedocs.io/en/latest/configuration/production.html`n`n# kinto.http_scheme = https`n# kinto.http_host = kinto.services.mozilla.com`n`n# Cross Origin Requests`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#cross-origin-requests-cors`n#`n# kinto.cors_origins = *`n`n# Backoff indicators/end of service`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#backoff-indicators`n# https://kinto.readthedocs.io/en/latest/api/1.x/backoff.html#id1`n#`n# kinto.backoff =`n# kinto.backoff_percentage =`n# kinto.retry_after_seconds = 3`n# kinto.eos =`n# kinto.eos_message =`n# kinto.eos_url =`n`n# Project information`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#project-information`n#`n# kinto.version_json_path = ./version.json`n# kinto.error_info_link = https://github.com/kinto/kinto/issues/`n# kinto.project_docs = https://kinto.readthedocs.io`n# kinto.project_name = kinto`n# kinto.project_version =`n# kinto.version_prefix_redirect_enabled = true`n`n# Application profilling`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#application-profiling`n# kinto.profiler_enabled = true`n# kinto.profiler_dir = /tmp/profiling`n`n# Client cache headers`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#client-caching`n#`n# Every bucket objects objects and list`n# kinto.bucket_cache_expires_seconds = 3600`n#`n# Every collection objects and list of every buckets`n# kinto.collection_cache_expires_seconds = 3600`n#`n# Every group objects and list of every buckets`n# kinto.group_cache_expires_seconds = 3600`n#`n# Every records objects and list of every collections`n# kinto.record_cache_expires_seconds = 3600`n#`n# Records in a specific bucket`n# kinto.blog_record_cache_expires_seconds = 3600`n#`n# Records in a specific collection in a specific bucket`n# kinto.blog_article_record_cache_expires_seconds = 3600`n`n# Custom ID generator for POST Requests`n# https://kinto.readthedocs.io/en/latest/tutorials/custom-id-generator.html#tutorial-id-generator`n#`n# Default generator`n# kinto.bucket_id_generator=kinto.views.NameGenerator`n# Custom example`n# kinto.collection_id_generator = name_generator.CollectionGenerator`n# kinto.group_id_generator = name_generator.GroupGenerator`n# kinto.record_id_generator = name_generator.RecordGenerator`n`n# Enabling or disabling endpoints`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#enabling-or-disabling-endpoints`n#`n# This is a rather confusing setting due to naming conventions used in kinto.core`n# For a more in depth explanation, refer to https://github.com/Kinto/kinto/issues/710`n# kinto.endpoint_type_resource_name_method_enabled = false`n# Where:`n# endpoint_type: is either ````collection```` (plural, e.g. ````/buckets````) or ````record```` (single, e.g. ````/buckets/abc````);`n# resource_name: is the name of the resource (e.g. ````bucket````, ````group````, ````collection````, ````record````);`n# method: is the http method (in lower case) (e.g. ````get````, ````post````, ````put````, ````patch````, ````delete````).`n# For example, to disable the POST on the list of buckets and DELETE on single records`n# kinto.collection_bucket_post_enabled = false`n# kinto.record_record_delete_enabled = false`n`n# `[uwsgi`]`n# wsgi-file = app.wsgi`n# enable-threads = true`n# socket = /var/run/uwsgi/kinto.sock`n# chmod-socket = 666`n# processes =  3`n# master = true`n# module = kinto`n# harakiri = 120`n# uid = kinto`n# gid = kinto`n# virtualenv = .venv`n# lazy = true`n# lazy-apps = true`n# single-interpreter = true`n# buffer-size = 65535`n# post-buffering = 65535`n# plugin = python`n`n# Logging and Monitoring`n#`n# https://kinto.readthedocs.io/en/latest/configuration/settings.html#logging-and-monitoring`n# kinto.statsd_backend = kinto.core.statsd`n# kinto.statsd_prefix = kinto`n# kinto.statsd_url =`n`n# kinto.newrelic_config =`n# kinto.newrelic_env = dev`n`n# Logging configuration`n`n`[loggers`]`nkeys = root, kinto`n`n`[handlers`]`nkeys = console`n`n`[formatters`]`nkeys = color`n`n`[logger_root`]`nlevel = INFO`nhandlers = console`n`n`[logger_kinto`]`nlevel = DEBUG`nhandlers = console`nqualname = kinto`n`n`[handler_console`]`nclass = StreamHandler`nargs = (sys.stderr,)`nlevel = NOTSET`nformatter = color`n`n`[formatter_color`]`nclass = logging_color_formatter.ColorFormatter"
	}
	try{
		if(-NOT(Test-Path $To)){Set-Content -Path $To -Value $template -Encoding 'Ascii'}
	}catch{Write-Error $_}
}

function Invoke-Kinto {
	if(-NOT $Help -AND ($Install -OR $Setup -OR $Run -OR $Test)) {
		if($Install){iex "pip install -r $RequirementsFile"}
		if($Setup){iex "python setup.py install"}
		if($Run){
			$checkpoint = $PWD.Path
			if(-NOT (Test-Path $KINTO_INI)) {Create-IniTemplate -From $KINTO_INI}
			iex "kinto migrate --ini $KINTO_INI;kinto start --ini $KINTO_INI --port $PORT"
			cd $PWD
		}
	} elseif ($Help) {
		Get-Help Kinto-Help -Full | more
	} else { Get-Help Kinto-Help -Example | more }
}

icm -ScriptBlock {ValidateVersions} | Out-Null

Invoke-Kinto
