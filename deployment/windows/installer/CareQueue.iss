#define MyAppName "CareQueue"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "CareQueue"
#define MyAppURL "https://github.com/BlessedCow/CareQueue"
#define MyAppExeName "CareQueue-Setup.exe"

[Setup]
AppId={{D692047A-3051-47D7-95C1-451C39702F44}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={autopf}\CareQueue
DisableDirPage=yes
DisableProgramGroupPage=yes
CreateAppDir=no
Uninstallable=no

PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=..\..\..\build\windows\installer
OutputBaseFilename=CareQueue-Setup-{#MyAppVersion}
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=CareQueue Windows Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright CareQueue

CloseApplications=no
RestartApplications=no
SetupLogging=yes
UsePreviousAppDir=no
UsePreviousLanguage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\..\build\windows\payload\*"; \
    DestDir: "{tmp}\CareQueuePayload"; \
    Flags: ignoreversion recursesubdirs createallsubdirs deleteafterinstall

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""C:\Program Files\CareQueue\deployment\windows\CareQueue-AdminSetup.ps1"""; \
    Description: "Launch First-Time Admin Account Setup"; \
    Flags: postinstall skipifsilent nowait

[Code]
const
  CareQueueApplicationOrigin = 'https://carequeue.local';
  CareQueueInstallDirectory = 'C:\Program Files\CareQueue';
  CareQueueDataDirectory = 'C:\ProgramData\CareQueue';

function CareQueueIsInstalled(): Boolean;
begin
  Result :=
    DirExists(
      AddBackslash(CareQueueInstallDirectory) +
      'backend\authstatus_api'
    ) and
    FileExists(
      AddBackslash(CareQueueInstallDirectory) +
      'frontend\dist\index.html'
    ) and
    FileExists(
      AddBackslash(CareQueueInstallDirectory) +
      'runtime\python\python.exe'
    ) and
    FileExists(
      AddBackslash(CareQueueInstallDirectory) +
      'vendor\caddy\caddy.exe'
    );
end;

function GetOperationMode(): String;
begin
  if CareQueueIsInstalled() then
    Result := 'Upgrade'
  else
    Result := 'Install';
end;

function QuoteArgument(const Value: String): String;
begin
  Result := '"' + Value + '"';
end;

function GetPowerShellPath(): String;
begin
  Result :=
    ExpandConstant(
      '{sys}\WindowsPowerShell\v1.0\powershell.exe'
    );

  if not FileExists(Result) then
    Result := ExpandConstant('{sys}\powershell.exe');
end;

function GetInstallerScriptPath(): String;
begin
  Result :=
    ExpandConstant(
      '{tmp}\CareQueuePayload\deployment\windows\' +
      'installer\invoke-install.ps1'
    );
end;

function GetInstallerParameters(): String;
var
  OperationMode: String;
begin
  OperationMode := GetOperationMode();

  Result :=
    '-NoProfile ' +
    '-NonInteractive ' +
    '-ExecutionPolicy Bypass ' +
    '-File ' +
    QuoteArgument(GetInstallerScriptPath()) +
    ' -Mode ' +
    OperationMode +
    ' -ApplicationOrigin ' +
    QuoteArgument(CareQueueApplicationOrigin) +
    ' -PayloadDirectory ' +
    QuoteArgument(
      ExpandConstant('{tmp}\CareQueuePayload')
    ) +
    ' -InstallDirectory ' +
    QuoteArgument(CareQueueInstallDirectory) +
    ' -DataDirectory ' +
    QuoteArgument(CareQueueDataDirectory);
end;

procedure RunCareQueueInstaller();
var
  PowerShellPath: String;
  InstallerParameters: String;
  InstallerExitCode: Integer;
  OperationMode: String;
begin
  PowerShellPath := GetPowerShellPath();
  InstallerParameters := GetInstallerParameters();
  OperationMode := GetOperationMode();

  Log(
    'Starting CareQueue operation: ' +
    OperationMode
  );

  Log(
    'PowerShell executable: ' +
    PowerShellPath
  );

  if not Exec(
    PowerShellPath,
    InstallerParameters,
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    InstallerExitCode
  ) then
  begin
    RaiseException(
      'CareQueue setup could not start the installer engine.'
    );
  end;

  Log(
    'CareQueue installer exit code: ' +
    IntToStr(InstallerExitCode)
  );

  if InstallerExitCode <> 0 then
  begin
    RaiseException(
      'CareQueue ' +
      OperationMode +
      ' failed with exit code ' +
      IntToStr(InstallerExitCode) +
      '.' +
      Chr(13) + Chr(10) +
      Chr(13) + Chr(10) +
      'Review the installer log under:' +
      Chr(13) + Chr(10) +
      'C:\ProgramData\CareQueue\Logs\Installer'
    );
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunCareQueueInstaller();
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;

  if PageID = wpSelectDir then
    Result := True
  else if PageID = wpSelectProgramGroup then
    Result := True;
end;

procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'This setup will install or upgrade CareQueue.' +
    Chr(13) + Chr(10) +
    Chr(13) + Chr(10) +
    'CareQueue will be installed as two Windows services and ' +
    'will be available at:' +
    Chr(13) + Chr(10) +
    'https://carequeue.local';
end;