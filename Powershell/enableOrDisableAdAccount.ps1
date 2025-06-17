Param(
    [Parameter(Mandatory=$true)]
    [string]$username
)

try {
    # Récupérer l'utilisateur AD avec sa propriété 'Enabled'
    $user = Get-ADUser -Identity $username -Properties Enabled -ErrorAction Stop

    Write-Host "Statut actuel : $($user.Enabled)"

    if ($user.Enabled -eq $true) {
        # L'utilisateur est activé, le désactiver
        Disable-ADAccount -Identity $username -ErrorAction Stop
        Write-Host "L'utilisateur '$username' a été désactivé avec succès."
    } else {
        # L'utilisateur est désactivé, l'activer
        Enable-ADAccount -Identity $username -ErrorAction Stop
        Write-Host "L'utilisateur '$username' a été activé avec succès."
    }
}
catch [Microsoft.ActiveDirectory.Management.ADIdentityNotFoundException] {
    Write-Error "L'utilisateur '$username' n'a pas été trouvé dans Active Directory."
}
catch {
    Write-Error "Une erreur inattendue est survenue : $($_.Exception.Message)"
}
