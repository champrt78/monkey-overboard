#!/usr/bin/env node
// Generate Monkey Overboard SFX via jsfxr + ffmpeg.
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const sfxr = require("jsfxr");

const OUT_DIR = path.resolve(__dirname, "..", "assets", "audio", "sfx");
fs.mkdirSync(OUT_DIR, { recursive: true });

function writeWav(params, outPath) {
	const sound = new sfxr.SoundEffect(params).generate();
	const regex = /^data:.+\/(.+);base64,(.*)$/;
	const matches = sound.dataURI.match(regex);
	const data = Buffer.from(matches[2], "base64");
	fs.writeFileSync(outPath, data);
}

function toOgg(wavPath, oggPath) {
	execSync(`ffmpeg -y -i "${wavPath}" -c:a libvorbis -q:a 4 "${oggPath}"`, { stdio: "ignore" });
	fs.unlinkSync(wavPath);
}

function generate(name, builder) {
	const p = new sfxr.Params();
	p.sound_vol = 0.5;
	p.sample_rate = 44100;
	p.sample_size = 8;
	builder(p);
	const wavPath = path.join(OUT_DIR, `${name}.wav`);
	const oggPath = path.join(OUT_DIR, `${name}.ogg`);
	writeWav(p, wavPath);
	toOgg(wavPath, oggPath);
	console.log(`  Saved ${name}.ogg`);
}

const SFX = [
	["launch", (p) => {
		p.jump();
		p.wave_type = 0; // SQUARE
		p.p_base_freq = 0.35;
		p.p_freq_ramp = 0.25;
		p.p_env_attack = 0;
		p.p_env_sustain = 0.05;
		p.p_env_decay = 0.15;
		p.p_env_punch = 0.2;
		p.p_duty = 0.5;
	}],
	["catch", (p) => {
		p.powerUp();
		p.wave_type = 2; // SINE
		p.p_base_freq = 0.5;
		p.p_freq_ramp = 0.25;
		p.p_env_attack = 0;
		p.p_env_sustain = 0.08;
		p.p_env_decay = 0.18;
		p.p_env_punch = 0.1;
	}],
	["banana", (p) => {
		p.pickupCoin();
		p.wave_type = 1; // SAWTOOTH
		p.p_base_freq = 0.6;
		p.p_env_attack = 0;
		p.p_env_sustain = 0.04;
		p.p_env_decay = 0.18;
		p.p_env_punch = 0.3;
		p.p_arp_speed = 0.6;
		p.p_arp_mod = 0.35;
	}],
	["splash", (p) => {
		p.hitHurt();
		p.wave_type = 3; // NOISE
		p.p_base_freq = 0.25;
		p.p_freq_ramp = -0.2;
		p.p_env_attack = 0;
		p.p_env_sustain = 0.05;
		p.p_env_decay = 0.25;
		p.p_env_punch = 0.1;
		p.p_lpf_freq = 0.5;
	}],
	["chomp", (p) => {
		p.hitHurt();
		p.wave_type = 3; // NOISE
		p.p_base_freq = 0.35;
		p.p_freq_ramp = -0.4;
		p.p_env_attack = 0;
		p.p_env_sustain = 0.04;
		p.p_env_decay = 0.15;
		p.p_env_punch = 0.3;
		p.p_hpf_freq = 0.2;
	}],
	["life_lost", (p) => {
		p.wave_type = 2; // SINE
		p.p_base_freq = 0.4;
		p.p_freq_ramp = -0.35;
		p.p_env_attack = 0;
		p.p_env_sustain = 0.15;
		p.p_env_decay = 0.45;
		p.p_env_punch = 0;
	}],
];

for (const [name, builder] of SFX) {
	console.log(`Generating ${name}.ogg ...`);
	generate(name, builder);
}

console.log("Done.");
