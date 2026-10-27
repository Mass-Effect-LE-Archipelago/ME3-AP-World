#pragma once
// Loadout weapons a WEAPON delivery may unlock. ME3 records an owned weapon as the player variable
// "SFXGameContent.<class>" = 1 (2026-10-26 save diff: Earth sets Predator and Avenger). The ids are the wire
// contract: append only. Source: base Coalesced SFXGame.SFXPlayerSquadLoadoutData (heavy weapons excluded;
// they are mission pickups, not loadout picks). DLC weapons are not listed yet.
#include <array>
#include <string_view>

namespace Weapons {
constexpr std::array<std::string_view, 44> Classes{
    // 0..11 assault rifles
    "SFXWeapon_AssaultRifle_Avenger", "SFXWeapon_AssaultRifle_Argus", "SFXWeapon_AssaultRifle_Cobra",
    "SFXWeapon_AssaultRifle_Collector", "SFXWeapon_AssaultRifle_Falcon", "SFXWeapon_AssaultRifle_Geth",
    "SFXWeapon_AssaultRifle_Mattock", "SFXWeapon_AssaultRifle_Reckoning", "SFXWeapon_AssaultRifle_Revenant",
    "SFXWeapon_AssaultRifle_Saber", "SFXWeapon_AssaultRifle_Valkyrie", "SFXWeapon_AssaultRifle_Vindicator",
    // 12..16 SMGs
    "SFXWeapon_SMG_Shuriken", "SFXWeapon_SMG_Hornet", "SFXWeapon_SMG_Hurricane", "SFXWeapon_SMG_Locust",
    "SFXWeapon_SMG_Tempest",
    // 17..24 heavy pistols (17 = Predator, the starting item)
    "SFXWeapon_Pistol_Predator", "SFXWeapon_Pistol_Carnifex", "SFXWeapon_Pistol_Eagle", "SFXWeapon_Pistol_Ivory",
    "SFXWeapon_Pistol_Phalanx", "SFXWeapon_Pistol_Scorpion", "SFXWeapon_Pistol_Talon", "SFXWeapon_Pistol_Thor",
    // 25..34 shotguns
    "SFXWeapon_Shotgun_Katana", "SFXWeapon_Shotgun_Claymore", "SFXWeapon_Shotgun_Crusader",
    "SFXWeapon_Shotgun_Disciple", "SFXWeapon_Shotgun_Eviscerator", "SFXWeapon_Shotgun_Geth",
    "SFXWeapon_Shotgun_Graal", "SFXWeapon_Shotgun_Raider", "SFXWeapon_Shotgun_Scimitar",
    "SFXWeapon_Shotgun_Striker",
    // 35..43 sniper rifles
    "SFXWeapon_SniperRifle_Mantis", "SFXWeapon_SniperRifle_BlackWidow", "SFXWeapon_SniperRifle_Incisor",
    "SFXWeapon_SniperRifle_Indra", "SFXWeapon_SniperRifle_Javelin", "SFXWeapon_SniperRifle_Raptor",
    "SFXWeapon_SniperRifle_Valiant", "SFXWeapon_SniperRifle_Viper", "SFXWeapon_SniperRifle_Widow",
};
constexpr int Predator = 17;
}
