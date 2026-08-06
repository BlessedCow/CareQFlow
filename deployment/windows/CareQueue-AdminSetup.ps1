[CmdletBinding()]
param(
    [string]$SetupEndpoint = "http://127.0.0.1:8000/api/security/setup-initial-admin",

    [string]$SetupStatusEndpoint = "http://127.0.0.1:8000/api/security/setup-initial-admin/status",

    [string]$HealthEndpoint = "http://127.0.0.1:8000/api/health",

    [string]$ApplicationUrl = "https://carequeue.local",

    [ValidateRange(1, 60)]
    [int]$HealthAttempts = 5,

    [ValidateRange(1, 10)]
    [int]$HealthDelaySeconds = 2
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

function Test-CareQueueApiReady {
    param(
        [Parameter(Mandatory)]
        [string]$Endpoint,

        [Parameter(Mandatory)]
        [int]$Attempts,

        [Parameter(Mandatory)]
        [int]$DelaySeconds
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt += 1) {
        try {
            Invoke-RestMethod `
                -Method Get `
                -Uri $Endpoint `
                -TimeoutSec 2 | Out-Null

            return $true
        }
        catch {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    return $false
}

function Get-InitialAdminSetupAvailable {
    param(
        [Parameter(Mandatory)]
        [string]$Endpoint
    )

    $response = Invoke-RestMethod `
        -Method Get `
        -Uri $Endpoint `
        -TimeoutSec 10

    return [bool]$response.setup_available
}

function New-SetupPayload {
    param(
        [Parameter(Mandatory)]
        [string]$Username,

        [Parameter(Mandatory)]
        [string]$Secret
    )

    return @{
        username = $Username
        password = $Secret
    } | ConvertTo-Json -Compress
}

$xaml = @"
<Window
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    Title="CareQueue First-Time Admin Setup"
    Height="530"
    Width="560"
    MinHeight="530"
    MinWidth="560"
    WindowStartupLocation="CenterScreen"
    ResizeMode="NoResize"
    Background="#F8FAFC">
    <Grid Margin="28">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />
            <RowDefinition Height="Auto" />
            <RowDefinition Height="Auto" />
            <RowDefinition Height="Auto" />
            <RowDefinition Height="Auto" />
            <RowDefinition Height="*" />
            <RowDefinition Height="Auto" />
        </Grid.RowDefinitions>

        <TextBlock
            Grid.Row="0"
            Text="Create the first CareQueue admin"
            FontSize="24"
            FontWeight="SemiBold"
            Foreground="#0F172A"
            Margin="0,0,0,8" />

        <TextBlock
            Grid.Row="1"
            Text="This one-time setup creates the first administrator account through the local CareQueue API. Passwords are never passed through command-line arguments."
            TextWrapping="Wrap"
            FontSize="13"
            Foreground="#475569"
            Margin="0,0,0,24" />

        <StackPanel Grid.Row="2" Margin="0,0,0,14">
            <TextBlock
                Text="Admin username"
                FontSize="13"
                FontWeight="SemiBold"
                Foreground="#334155"
                Margin="0,0,0,6" />

            <TextBox
                Name="UsernameBox"
                Height="36"
                FontSize="14"
                Padding="8,5" />
        </StackPanel>

        <StackPanel Grid.Row="3" Margin="0,0,0,14">
            <TextBlock
                Text="Password"
                FontSize="13"
                FontWeight="SemiBold"
                Foreground="#334155"
                Margin="0,0,0,6" />

            <PasswordBox
                Name="PasswordBox"
                Height="36"
                FontSize="14"
                Padding="8,5" />
        </StackPanel>

        <StackPanel Grid.Row="4" Margin="0,0,0,16">
            <TextBlock
                Text="Confirm password"
                FontSize="13"
                FontWeight="SemiBold"
                Foreground="#334155"
                Margin="0,0,0,6" />

            <PasswordBox
                Name="ConfirmPasswordBox"
                Height="36"
                FontSize="14"
                Padding="8,5" />
        </StackPanel>

        <Border
            Grid.Row="5"
            Name="StatusPanel"
            Background="#E2E8F0"
            CornerRadius="8"
            Padding="12"
            MinHeight="74"
            Margin="0,0,0,18"
            VerticalAlignment="Stretch">
            <TextBlock
                Name="StatusText"
                Text="Checking CareQueue setup status..."
                TextWrapping="Wrap"
                FontSize="13"
                Foreground="#334155" />
        </Border>

        <StackPanel
            Grid.Row="6"
            Orientation="Horizontal"
            HorizontalAlignment="Right"
            Margin="0,0,0,0">
            <Button
                Name="CancelButton"
                Content="Cancel"
                Width="104"
                Height="38"
                Margin="0,0,10,0" />

            <Button
                Name="CreateButton"
                Content="Create admin"
                Width="132"
                Height="38"
                IsDefault="True" />
        </StackPanel>
    </Grid>
</Window>
"@

$reader = [System.Xml.XmlReader]::Create(
    [System.IO.StringReader]::new($xaml)
)

$window = [Windows.Markup.XamlReader]::Load($reader)

$usernameBox = $window.FindName("UsernameBox")
$passwordBox = $window.FindName("PasswordBox")
$confirmPasswordBox = $window.FindName("ConfirmPasswordBox")
$statusPanel = $window.FindName("StatusPanel")
$statusText = $window.FindName("StatusText")
$createButton = $window.FindName("CreateButton")
$cancelButton = $window.FindName("CancelButton")

$script:setupAlreadyComplete = $false

function Set-SetupStatus {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet("Info", "Error", "Success")]
        [string]$Kind = "Info"
    )

    $statusText.Text = $Message

    if ($Kind -eq "Error") {
        $statusPanel.Background = "#FEE2E2"
        $statusText.Foreground = "#991B1B"
        return
    }

    if ($Kind -eq "Success") {
        $statusPanel.Background = "#DCFCE7"
        $statusText.Foreground = "#166534"
        return
    }

    $statusPanel.Background = "#E2E8F0"
    $statusText.Foreground = "#334155"
}

function Set-SetupFormEnabled {
    param(
        [Parameter(Mandatory)]
        [bool]$Enabled
    )

    $usernameBox.IsEnabled = $Enabled
    $passwordBox.IsEnabled = $Enabled
    $confirmPasswordBox.IsEnabled = $Enabled
}

function Start-SetupStatusCheck {
    $window.Dispatcher.BeginInvoke(
        [Action] {
            try {
                if (
                    -not (
                        Test-CareQueueApiReady `
                            -Endpoint $HealthEndpoint `
                            -Attempts $HealthAttempts `
                            -DelaySeconds $HealthDelaySeconds
                    )
                ) {
                    throw "The local CareQueue API is not responding on 127.0.0.1:8000."
                }

                $setupAvailable = Get-InitialAdminSetupAvailable `
                    -Endpoint $SetupStatusEndpoint

                if (-not $setupAvailable) {
                    $script:setupAlreadyComplete = $true
                    $createButton.Content = "Open CareQueue"
                    $createButton.IsEnabled = $true
                    Set-SetupFormEnabled -Enabled $false

                    Set-SetupStatus `
                        -Message "Initial admin setup is already complete. You can open CareQueue and sign in with the existing admin account." `
                        -Kind Success

                    return
                }

                Set-SetupFormEnabled -Enabled $true
                $createButton.IsEnabled = $true

                Set-SetupStatus `
                    -Message "Enter a username and a password with at least 12 characters." `
                    -Kind Info

                $usernameBox.Focus() | Out-Null
            }
            catch {
                $createButton.IsEnabled = $false
                Set-SetupFormEnabled -Enabled $false

                Set-SetupStatus `
                    -Message $_.Exception.Message `
                    -Kind Error
            }
        },
        [System.Windows.Threading.DispatcherPriority]::Background
    ) | Out-Null
}

$window.Add_ContentRendered({
        $createButton.IsEnabled = $false
        Set-SetupFormEnabled -Enabled $false

        Set-SetupStatus `
            -Message "Checking CareQueue setup status..." `
            -Kind Info

        Start-SetupStatusCheck
    })
$cancelButton.Add_Click({
        $window.Close()
    })

$createButton.Add_Click({
        if ($script:setupAlreadyComplete) {
            Start-Process $ApplicationUrl
            $window.Close()
            return
        }

        $username = $usernameBox.Text.Trim()
        $secret = $passwordBox.Password
        $confirmedSecret = $confirmPasswordBox.Password

        if ([string]::IsNullOrWhiteSpace($username)) {
            Set-SetupStatus `
                -Message "Enter an admin username." `
                -Kind Error
            return
        }

        if ($secret.Length -lt 12) {
            Set-SetupStatus `
                -Message "Password must be at least 12 characters." `
                -Kind Error
            return
        }

        if ($secret -ne $confirmedSecret) {
            Set-SetupStatus `
                -Message "Passwords do not match." `
                -Kind Error
            return
        }

        $createButton.IsEnabled = $false
        $cancelButton.IsEnabled = $false
        Set-SetupFormEnabled -Enabled $false

        try {
            Set-SetupStatus `
                -Message "Creating the initial administrator account..." `
                -Kind Info

            $body = New-SetupPayload `
                -Username $username `
                -Secret $secret

            Invoke-RestMethod `
                -Method Post `
                -Uri $SetupEndpoint `
                -Body $body `
                -ContentType "application/json" `
                -TimeoutSec 15 | Out-Null

            $passwordBox.Clear()
            $confirmPasswordBox.Clear()

            Set-SetupStatus `
                -Message "Setup complete. Launching CareQueue..." `
                -Kind Success

            Start-Process $ApplicationUrl

            $window.Close()
        }
        catch {
            $passwordBox.Clear()
            $confirmPasswordBox.Clear()

            $message = $_.Exception.Message

            if ($message -like "*409*") {
                $message = "Initial admin setup is no longer available because a user already exists."
                $script:setupAlreadyComplete = $true
                $createButton.Content = "Open CareQueue"
            }
            elseif ($message -like "*400*") {
                $message = "The setup request was rejected. Check the username and password, then try again."
            }

            Set-SetupStatus `
                -Message $message `
                -Kind Error
        }
        finally {
            if ($script:setupAlreadyComplete) {
                Set-SetupFormEnabled -Enabled $false
                $createButton.IsEnabled = $true
            }
            else {
                Set-SetupFormEnabled -Enabled $true
                $createButton.IsEnabled = $true
            }

            $cancelButton.IsEnabled = $true
        }
    })

$window.ShowDialog() | Out-Null