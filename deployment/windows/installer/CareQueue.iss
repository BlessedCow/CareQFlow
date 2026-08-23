#define MyAppName "CareQueue"
#define MyAppVersion "0.3.0"
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
    Flags: postinstall skipifsilent nowait; \
    Check: ShouldOfferAdminSetup
  
[Code]
const
  CareQueueApplicationOrigin = 'https://carequeue.local';
  CareQueueInstallDirectory = 'C:\Program Files\CareQueue';
  CareQueueDataDirectory = 'C:\ProgramData\CareQueue';
var
  OperationModePage: TInputOptionWizardPage;
  SelectedOperationMode: String;

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
  if SelectedOperationMode <> '' then
  begin
    Result := SelectedOperationMode;
    exit;
  end;

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

function ShouldOfferAdminSetup(): Boolean;
begin
  Result := GetOperationMode() <> 'Uninstall';
end;

function GetInstallerScriptPath(): String;
begin
  Result :=
    ExpandConstant(
      '{tmp}\CareQueuePayload\deployment\windows\' +
      'installer\invoke-install.ps1'
    );
end;

function UpdateReadyMemo(
  Space: String;
  NewLine: String;
  MemoUserInfoInfo: String;
  MemoDirInfo: String;
  MemoTypeInfo: String;
  MemoComponentsInfo: String;
  MemoGroupInfo: String;
  MemoTasksInfo: String
): String;
var
  OperationMode: String;
begin
  OperationMode := GetOperationMode();

  if OperationMode = 'Uninstall' then
  begin
    Result :=
      'Setup is ready to uninstall CareQueue from this computer.' +
      NewLine +
      NewLine +
      'CareQueue Windows services and application files will be removed.' +
      NewLine +
      'Runtime data in C:\ProgramData\CareQueue will be preserved.';
    exit;
  end;

  if OperationMode = 'Repair' then
  begin
    Result :=
      'Setup is ready to repair the existing CareQueue installation.' +
      NewLine +
      NewLine +
      'CareQueue application files, services, and packaged runtime files will be restored.' +
      NewLine +
      'Existing runtime data and secrets will be preserved.';
    exit;
  end;

  if OperationMode = 'Upgrade' then
  begin
    Result :=
      'Setup is ready to upgrade the existing CareQueue installation.' +
      NewLine +
      NewLine +
      'CareQueue application files, services, and packaged runtime files will be updated.' +
      NewLine +
      'Existing runtime data and secrets will be preserved.';
    exit;
  end;

  Result :=
    'Setup is ready to install CareQueue.' +
    NewLine +
    NewLine +
    'CareQueue will be installed as Windows services and made available at:' +
    NewLine +
    CareQueueApplicationOrigin;
end;

procedure SetSelectedOperationMode();
begin
  if OperationModePage = nil then
  begin
    SelectedOperationMode := GetOperationMode();
    exit;
  end;

  if OperationModePage.Values[0] then
    SelectedOperationMode := 'Upgrade'
  else if OperationModePage.Values[1] then
    SelectedOperationMode := 'Repair'
  else if OperationModePage.Values[2] then
    SelectedOperationMode := 'Uninstall'
  else
    SelectedOperationMode := 'Upgrade';
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

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if (OperationModePage <> nil) and
     (CurPageID = OperationModePage.ID) then
    SetSelectedOperationMode();
end;

procedure CurPageChanged(CurPageID: Integer);
var
  OperationMode: String;
begin
  OperationMode := GetOperationMode();

  if CurPageID = wpReady then
  begin
    if OperationMode = 'Uninstall' then
    begin
      WizardForm.NextButton.Caption := '&Uninstall';
      WizardForm.ReadyLabel.Caption :=
        'Click Uninstall to remove CareQueue application files and services.';
    end
    else if OperationMode = 'Repair' then
    begin
      WizardForm.NextButton.Caption := '&Repair';
      WizardForm.ReadyLabel.Caption :=
        'Click Repair to repair the existing CareQueue installation.';
    end
    else if OperationMode = 'Upgrade' then
    begin
      WizardForm.NextButton.Caption := '&Upgrade';
      WizardForm.ReadyLabel.Caption :=
        'Click Upgrade to upgrade the existing CareQueue installation.';
    end
    else
    begin
      WizardForm.NextButton.Caption := '&Install';
      WizardForm.ReadyLabel.Caption :=
        'Click Install to begin installing CareQueue.';
    end;
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
  SelectedOperationMode := '';

  if CareQueueIsInstalled() then
  begin
    WizardForm.WelcomeLabel2.Caption :=
      'CareQueue is already installed.' +
      Chr(13) + Chr(10) +
      Chr(13) + Chr(10) +
      'Choose whether to upgrade, repair, or uninstall the existing installation.';

    OperationModePage :=
      CreateInputOptionPage(
        wpWelcome,
        'Choose CareQueue operation',
        'Select what you want the setup program to do.',
        'CareQueue is already installed on this computer.',
        True,
        False
      );

    OperationModePage.Add(
      'Upgrade existing installation'
    );

    OperationModePage.Add(
      'Repair existing installation'
    );

    OperationModePage.Add(
      'Uninstall CareQueue'
    );

    OperationModePage.Values[0] := True;
  end
  else
  begin
    WizardForm.WelcomeLabel2.Caption :=
      'This setup will install CareQueue.' +
      Chr(13) + Chr(10) +
      Chr(13) + Chr(10) +
      'CareQueue will be installed as two Windows services and ' +
      'will be available at:' +
      Chr(13) + Chr(10) +
      'https://carequeue.local';
  end;
end;