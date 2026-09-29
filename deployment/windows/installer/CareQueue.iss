#define MyAppName "CareQFlow"
#define MyAppVersion "0.7.0"
#define MyAppPublisher "CareQFlow"
#define MyAppURL "https://github.com/BlessedCow/CareQueue"
#define MyAppExeName "CareQFlow-Setup.exe"

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
OutputBaseFilename=CareQFlow-Setup-{#MyAppVersion}
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\..\..\build\windows\payload\LICENSE

VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=CareQFlow Windows Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright CareQFlow

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
  CareQueueApplicationOrigin = 'https://careqflow.local';
  CareQueueInstallDirectory = 'C:\Program Files\CareQueue';
  CareQueueDataDirectory = 'C:\ProgramData\CareQueue';
  CareQueueInstallStatePath =
    'C:\ProgramData\CareQueue\Config\install-state.json';
  CareQueueUpgradeRecoveryDirectory =
    'C:\ProgramData\CareQueue\Recovery\Upgrades';
var
  OperationModePage: TInputOptionWizardPage;
  NetworkModePage: TInputOptionWizardPage;
  SelectedOperationMode: String;
  SelectedNetworkMode: String;
  RollbackOperationAvailable: Boolean;
  LanAddressPage: TInputQueryWizardPage;

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

function GetInstalledNetworkMode(): String;
var
  InstallStateContent: AnsiString;
  StateText: String;
begin
  Result := 'LocalOnly';

  if not FileExists(CareQueueInstallStatePath) then
    exit;

  if not LoadStringFromFile(
    CareQueueInstallStatePath,
    InstallStateContent
  ) then
    exit;

  StateText := String(InstallStateContent);

  if (
    Pos(
      '"network_mode": "SecureLan"',
      StateText
    ) > 0
  ) or (
    Pos(
      '"network_mode":"SecureLan"',
      StateText
    ) > 0
  ) then
    Result := 'SecureLan';
end;

function ExtractJsonStringValue(
  const JsonText: String;
  const Key: String
): String;
var
  KeyMarker: String;
  RemainingText: String;
  ValueText: String;
  KeyPosition: Integer;
  ColonPosition: Integer;
  FirstQuotePosition: Integer;
  SecondQuotePosition: Integer;
begin
  Result := '';
  KeyMarker := '"' + Key + '"';
  KeyPosition := Pos(KeyMarker, JsonText);

  if KeyPosition = 0 then
    exit;

  RemainingText :=
    Copy(
      JsonText,
      KeyPosition + Length(KeyMarker),
      Length(JsonText)
    );

  ColonPosition := Pos(':', RemainingText);

  if ColonPosition = 0 then
    exit;

  ValueText :=
    Copy(
      RemainingText,
      ColonPosition + 1,
      Length(RemainingText)
    );

  FirstQuotePosition := Pos('"', ValueText);

  if FirstQuotePosition = 0 then
    exit;

  ValueText :=
    Copy(
      ValueText,
      FirstQuotePosition + 1,
      Length(ValueText)
    );

  SecondQuotePosition := Pos('"', ValueText);

  if SecondQuotePosition = 0 then
    exit;

  Result :=
    Copy(
      ValueText,
      1,
      SecondQuotePosition - 1
    );
end;

function GetInstalledApplicationOrigin(): String;
var
  InstallStateContent: AnsiString;
  InstalledOrigin: String;
begin
  Result := CareQueueApplicationOrigin;

  if not FileExists(CareQueueInstallStatePath) then
    exit;

  if not LoadStringFromFile(
    CareQueueInstallStatePath,
    InstallStateContent
  ) then
    exit;

  InstalledOrigin :=
    ExtractJsonStringValue(
      String(InstallStateContent),
      'application_origin'
    );

  if InstalledOrigin <> '' then
    Result := InstalledOrigin;
end;

function GetInstalledLanAddress(): String;
var
  InstalledOrigin: String;
begin
  Result := '';
  InstalledOrigin := GetInstalledApplicationOrigin();

  if Pos('https://', InstalledOrigin) <> 1 then
    exit;

  Result :=
    Copy(
      InstalledOrigin,
      Length('https://') + 1,
      Length(InstalledOrigin)
    );

  while (
    Length(Result) > 0
  ) and (
    Result[Length(Result)] = '/'
  ) do
    Delete(Result, Length(Result), 1);

  if Pos('/', Result) > 0 then
    Result := '';
end;

function CareQueueHasFailedUpgradeRecovery(): Boolean;
var
  FindRec: TFindRec;
  RecoveryPath: String;
  RecoveryContent: AnsiString;
begin
  Result := False;

  if not DirExists(CareQueueUpgradeRecoveryDirectory) then
    exit;

  RecoveryPath :=
    AddBackslash(CareQueueUpgradeRecoveryDirectory) +
    'upgrade-*.json';

  if FindFirst(RecoveryPath, FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) = 0 then
        begin
          if LoadStringFromFile(
            AddBackslash(CareQueueUpgradeRecoveryDirectory) +
            FindRec.Name,
            RecoveryContent
          ) then
          begin
            if Pos(
              '"status": "failed"',
              String(RecoveryContent)
            ) > 0 then
            begin
              Result := True;
              exit;
            end;
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
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

function GetNetworkMode(): String;
begin
  if SelectedNetworkMode <> '' then
  begin
    Result := SelectedNetworkMode;
    exit;
  end;

  if CareQueueIsInstalled() then
    Result := GetInstalledNetworkMode()
  else
    Result := 'LocalOnly';
end;


function GetApplicationOrigin(): String;
var
  LanAddress: String;
begin
  if GetNetworkMode() <> 'SecureLan' then
  begin
    Result := CareQueueApplicationOrigin;
    exit;
  end;

  LanAddress := '';

  if LanAddressPage <> nil then
    LanAddress := Trim(LanAddressPage.Values[0]);

  if LanAddress <> '' then
  begin
    Result :=
      'https://' +
      LanAddress;
    exit;
  end;

  if CareQueueIsInstalled() then
  begin
    Result := GetInstalledApplicationOrigin();
    exit;
  end;

  Result := CareQueueApplicationOrigin;
end;


procedure SetSelectedNetworkMode();
begin
  if NetworkModePage = nil then
  begin
    SelectedNetworkMode := GetNetworkMode();
    exit;
  end;

  if NetworkModePage.Values[1] then
    SelectedNetworkMode := 'SecureLan'
  else
    SelectedNetworkMode := 'LocalOnly';
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
var
  OperationMode: String;
begin
  OperationMode := GetOperationMode();

  Result :=
    (OperationMode <> 'Uninstall') and
    (OperationMode <> 'Rollback');
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
      'Setup is ready to uninstall CareQFlow from this computer.' +
      NewLine +
      NewLine +
      'CareQFlow Windows services and application files will be removed.' +
      NewLine +
      'Runtime data in C:\ProgramData\CareQueue will be preserved.';
    exit;
  end;

  if OperationMode = 'Repair' then
  begin
    Result :=
      'Setup is ready to repair the existing CareQFlow installation.' +
      NewLine +
      NewLine +
      'CareQFlow application files, services, and packaged runtime files will be restored.' +
      NewLine +
      'Existing runtime data and secrets will be preserved.';
    exit;
  end;

  if OperationMode = 'Upgrade' then
  begin
    Result :=
      'Setup is ready to upgrade the existing CareQFlow installation.' +
      NewLine +
      NewLine +
      'CareQFlow application files, services, and packaged runtime files will be updated.' +
      NewLine +
      'Existing runtime data and secrets will be preserved.';
    exit;
  end;

  if OperationMode = 'Rollback' then
  begin
    Result :=
      'Setup is ready to roll back the most recent failed CareQFlow upgrade.' +
      NewLine +
      NewLine +
      'The verified pre-upgrade application and database recovery assets will be restored.' +
      NewLine +
      'Rollback will stop if the required recovery assets cannot be validated.';
    exit;
  end;

  Result :=
    'Setup is ready to install CareQFlow.' +
    NewLine +
    NewLine +
    'CareQFlow will be installed as Windows services and made available at:' +
    NewLine +
    GetApplicationOrigin();
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
  else if RollbackOperationAvailable and
          OperationModePage.Values[2] then
    SelectedOperationMode := 'Rollback'
  else if RollbackOperationAvailable and
          OperationModePage.Values[3] then
    SelectedOperationMode := 'Uninstall'
  else if (not RollbackOperationAvailable) and
          OperationModePage.Values[2] then
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
    QuoteArgument(GetApplicationOrigin()) +
    ' -PayloadDirectory ' +
    QuoteArgument(
      ExpandConstant('{tmp}\CareQueuePayload')
    ) +
    ' -InstallDirectory ' +
    QuoteArgument(CareQueueInstallDirectory) +
    ' -DataDirectory ' +
    QuoteArgument(CareQueueDataDirectory);
      if (
        OperationMode <> 'Uninstall'
      ) and (
        OperationMode <> 'Rollback'
      ) then
      begin
        Result :=
          Result +
          ' -NetworkMode ' +
          QuoteArgument(GetNetworkMode());
      end;
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
    'Starting CareQFlow operation: ' +
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
      'CareQFlow setup could not start the installer engine.'
    );
  end;

  Log(
    'CareQFlow installer exit code: ' +
    IntToStr(InstallerExitCode)
  );

  if InstallerExitCode <> 0 then
  begin
    RaiseException(
      'CareQFlow ' +
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
  begin
    SetSelectedOperationMode();
    exit;
  end;

  if (NetworkModePage <> nil) and
     (CurPageID = NetworkModePage.ID) then
  begin
    SetSelectedNetworkMode();

    if SelectedNetworkMode = 'SecureLan' then
    begin
      Result :=
        MsgBox(
          'Secure LAN access allows devices on the same ' +
          'Windows Private network and local subnet to reach ' +
          'CareQFlow over HTTPS.' +
          Chr(13) + Chr(10) +
          Chr(13) + Chr(10) +
          'CareQFlow will not be opened on Public Windows ' +
          'networks, and the backend API remains bound to ' +
          'localhost.' +
          Chr(13) + Chr(10) +
          Chr(13) + Chr(10) +
          'Do not use router port forwarding to expose ' +
          'CareQFlow directly to the public internet.' +
          Chr(13) + Chr(10) +
          Chr(13) + Chr(10) +
          'Enable Secure LAN access?',
          mbConfirmation,
          MB_YESNO
        ) = IDYES;
    end;
  end;

  if (LanAddressPage <> nil) and
     (CurPageID = LanAddressPage.ID) then
  begin
    if Trim(LanAddressPage.Values[0]) = '' then
    begin
      MsgBox(
        'Enter the private IPv4 address assigned to this ' +
        'CareQFlow host.',
        mbError,
        MB_OK
      );

      Result := False;
      exit;
    end;

    if Pos(
      '://',
      LanAddressPage.Values[0]
    ) > 0 then
    begin
      MsgBox(
        'Enter only the IPv4 address, such as 192.168.1.50. ' +
        'Do not include https:// or a port.',
        mbError,
        MB_OK
      );

      Result := False;
      exit;
    end;
  end;
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
        'Click Uninstall to remove CareQFlow application files and services.';
    end
    else if OperationMode = 'Repair' then
    begin
      WizardForm.NextButton.Caption := '&Repair';
      WizardForm.ReadyLabel.Caption :=
        'Click Repair to repair the existing CareQFlow installation.';
    end
    else if OperationMode = 'Upgrade' then
    begin
      WizardForm.NextButton.Caption := '&Upgrade';
      WizardForm.ReadyLabel.Caption :=
        'Click Upgrade to upgrade the existing CareQFlow installation.';
    end
    else if OperationMode = 'Rollback' then
    begin
      WizardForm.NextButton.Caption := '&Rollback';
      WizardForm.ReadyLabel.Caption :=
        'Click Rollback to recover from the most recent failed CareQFlow upgrade.';
    end
    else
    begin
      WizardForm.NextButton.Caption := '&Install';
      WizardForm.ReadyLabel.Caption :=
        'Click Install to begin installing CareQFlow.';
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunCareQueueInstaller();
end;

function ShouldSkipPage(PageID: Integer): Boolean;
var
  OperationMode: String;
begin
  Result := False;
  OperationMode := GetOperationMode();

  if (
    NetworkModePage <> nil
  ) and (
    PageID = NetworkModePage.ID
  ) then
  begin
    Result :=
      (OperationMode = 'Rollback') or
      (OperationMode = 'Uninstall');

    exit;
  end;

  if (
    LanAddressPage <> nil
  ) and (
    PageID = LanAddressPage.ID
  ) then
  begin
    Result :=
      (OperationMode = 'Rollback') or
      (OperationMode = 'Uninstall') or
      (GetNetworkMode() <> 'SecureLan');

    exit;
  end;

  if PageID = wpSelectDir then
    Result := True
  else if PageID = wpSelectProgramGroup then
    Result := True
  else if PageID = wpLicense then
  begin
    Result :=
      (OperationMode = 'Repair') or
      (OperationMode = 'Rollback') or
      (OperationMode = 'Uninstall');
  end;
end;

procedure InitializeWizard();
var
  NetworkModeAfterPageId: Integer;
begin
  SelectedOperationMode := '';
  SelectedNetworkMode := '';
  RollbackOperationAvailable :=
    CareQueueHasFailedUpgradeRecovery();

  if CareQueueIsInstalled() then
  begin
    if RollbackOperationAvailable then
      WizardForm.WelcomeLabel2.Caption :=
        'CareQFlow is already installed.' +
        Chr(13) + Chr(10) +
        Chr(13) + Chr(10) +
        'Choose whether to upgrade, repair, roll back, or uninstall the existing installation.'
    else
      WizardForm.WelcomeLabel2.Caption :=
        'CareQFlow is already installed.' +
        Chr(13) + Chr(10) +
        Chr(13) + Chr(10) +
        'Choose whether to upgrade, repair, or uninstall the existing installation.';

    OperationModePage :=
      CreateInputOptionPage(
        wpWelcome,
        'Choose CareQFlow operation',
        'Select what you want the setup program to do.',
        'CareQFlow is already installed on this computer.',
        True,
        False
      );

    OperationModePage.Add(
      'Upgrade existing installation'
    );

    OperationModePage.Add(
      'Repair existing installation'
    );

    if RollbackOperationAvailable then
      OperationModePage.Add(
        'Roll back most recent failed upgrade'
      );

    OperationModePage.Add(
      'Uninstall CareQFlow'
    );

    OperationModePage.Values[0] := True;
    NetworkModeAfterPageId := OperationModePage.ID;
  end
  else
  begin
    WizardForm.WelcomeLabel2.Caption :=
      'This setup will install CareQFlow.' +
      Chr(13) + Chr(10) +
      Chr(13) + Chr(10) +
      'CareQFlow will be installed as two Windows services.' +
      Chr(13) + Chr(10) +
      'You can keep access local to this computer or enable ' +
      'Secure LAN access for trusted devices.';

    NetworkModeAfterPageId := wpWelcome;
  end;

  NetworkModePage :=
    CreateInputOptionPage(
      NetworkModeAfterPageId,
      'Choose CareQFlow network access',
      'Select which devices can reach this CareQFlow installation.',
      'Local only is the safest default. Secure LAN should only ' +
      'be enabled on a trusted Windows Private network.',
      True,
      False
    );

  NetworkModePage.Add(
    'Local only - use CareQFlow on this computer'
  );

  NetworkModePage.Add(
    'Secure LAN - allow devices on the local private network'
  );

  if (
    CareQueueIsInstalled()
  ) and (
    GetInstalledNetworkMode() = 'SecureLan'
  ) then
    NetworkModePage.Values[1] := True
  else
    NetworkModePage.Values[0] := True;

  LanAddressPage :=
    CreateInputQueryPage(
      NetworkModePage.ID,
      'Configure Secure LAN address',
      'Enter the private IPv4 address of this CareQFlow host.',
      'Use a stable private address assigned to this computer. ' +
      'A DHCP reservation or static address is recommended.'
    );

  LanAddressPage.Add(
    'Private IPv4 address:',
    False
  );

  if (
    CareQueueIsInstalled()
  ) and (
    GetInstalledNetworkMode() = 'SecureLan'
  ) then
    LanAddressPage.Values[0] := GetInstalledLanAddress();
end;
