#version 450 core
in vec3 colour;
in float distanceFog;
in float effectAlpha;
in vec2 effectUV;
flat in int effectType;
out vec4 outputColour;
void main(){float alpha=effectAlpha;if(effectType>=2){float r=length(effectUV);if(r>1.)discard;alpha*=smoothstep(1.,.35,r);}float fog=1-exp(-distanceFog*.0003); outputColour=vec4(mix(colour,vec3(.34,.42,.46),fog),alpha);}
