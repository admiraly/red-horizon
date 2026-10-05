#version 450 core
in vec3 colour;
in float distanceFog;
out vec4 outputColour;
void main(){float fog=1-exp(-distanceFog*.0003);outputColour=vec4(mix(colour,vec3(.34,.42,.46),fog),1);}
